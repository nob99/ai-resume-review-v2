"""
Tests for YAML Prompt Loader
=============================

Test suite for the prompt loading system, verifying YAML parsing, caching,
variable substitution, and compatibility with existing hardcoded prompts.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open

from app.ai_agents.prompts.loader import (
    PromptLoader, 
    LoadedPrompt, 
    PromptVariableBuilder,
    build_structure_variables,
    build_appeal_variables,
    get_prompt_loader,
    load_prompt_cached
)


class TestLoadedPrompt:
    """Test LoadedPrompt functionality."""
    
    def test_loaded_prompt_creation(self):
        """Test basic LoadedPrompt creation."""
        prompt = LoadedPrompt(
            name="test_prompt",
            version="1.0.0",
            description="Test prompt",
            system_prompt="You are a test assistant.",
            user_prompt="Analyze this: {text}",
            variables=["text"],
            metadata={"model": "gpt-4"}
        )
        
        assert prompt.name == "test_prompt"
        assert prompt.version == "1.0.0"
        assert "text" in prompt.variables
        assert prompt.metadata["model"] == "gpt-4"
    
    def test_variable_substitution(self):
        """Test variable substitution in prompts."""
        prompt = LoadedPrompt(
            name="test_prompt",
            version="1.0.0", 
            description="Test",
            system_prompt="You are analyzing {industry} resumes.",
            user_prompt="Analyze this resume: {resume_text}",
            variables=["industry", "resume_text"],
            metadata={}
        )
        
        substituted = prompt.substitute_variables(
            industry="tech",
            resume_text="John Doe Software Engineer"
        )
        
        assert "tech" in substituted.system_prompt
        assert "John Doe Software Engineer" in substituted.user_prompt
        assert substituted.name == prompt.name  # Other fields preserved
    
    def test_missing_variable_validation(self):
        """Test validation of required variables."""
        prompt = LoadedPrompt(
            name="test_prompt",
            version="1.0.0",
            description="Test",
            system_prompt="System prompt",
            user_prompt="User prompt with {required_var}",
            variables=["required_var"],
            metadata={}
        )
        
        with pytest.raises(ValueError, match="Missing required variables"):
            prompt.substitute_variables()  # Missing required_var


class TestPromptLoader:
    """Test PromptLoader functionality."""
    
    @pytest.fixture
    def temp_prompts_dir(self):
        """Create a temporary prompts directory with test files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            prompts_dir = Path(tmp_dir) / "prompts"
            prompts_dir.mkdir()
            
            # Create test YAML file
            test_prompt = {
                'metadata': {
                    'name': 'test_analysis',
                    'version': '1.0.0',
                    'description': 'Test analysis prompt',
                    'model': 'gpt-4'
                },
                'prompts': {
                    'system': 'You are a test analyst.',
                    'user': 'Analyze: {content}'
                },
                'variables': [
                    {'name': 'content', 'type': 'string', 'required': True}
                ],
                'tags': ['test', 'analysis']
            }
            
            test_file = prompts_dir / "test_analysis_v1.yaml"
            with open(test_file, 'w') as f:
                yaml.dump(test_prompt, f)
            
            yield prompts_dir
    
    def test_loader_initialization(self, temp_prompts_dir):
        """Test PromptLoader initialization."""
        loader = PromptLoader(temp_prompts_dir)
        assert loader.prompts_dir == temp_prompts_dir
        assert loader._cache == {}
    
    def test_loader_initialization_default_path(self):
        """Test PromptLoader with default path."""
        with patch('pathlib.Path.exists', return_value=True):
            loader = PromptLoader()
            assert "templates" in str(loader.prompts_dir)
    
    def test_load_prompt_success(self, temp_prompts_dir):
        """Test successful prompt loading."""
        loader = PromptLoader(temp_prompts_dir)
        prompt = loader.load_prompt('test_analysis')
        
        assert prompt.name == 'test_analysis'
        assert prompt.version == '1.0.0'
        assert 'content' in prompt.variables
        assert 'test' in prompt.tags
        assert 'You are a test analyst' in prompt.system_prompt
    
    def test_load_prompt_caching(self, temp_prompts_dir):
        """Test that prompts are cached correctly."""
        loader = PromptLoader(temp_prompts_dir)
        
        # First load
        prompt1 = loader.load_prompt('test_analysis')
        cache_size_after_first = len(loader._cache)
        
        # Second load (should use cache)
        prompt2 = loader.load_prompt('test_analysis')
        cache_size_after_second = len(loader._cache)
        
        assert cache_size_after_first == 1
        assert cache_size_after_second == 1  # No new cache entry
        assert prompt1.name == prompt2.name
    
    def test_load_nonexistent_prompt(self, temp_prompts_dir):
        """Test loading a prompt that doesn't exist."""
        loader = PromptLoader(temp_prompts_dir)
        
        with pytest.raises(FileNotFoundError, match="Prompt not found"):
            loader.load_prompt('nonexistent_prompt')
    
    def test_get_available_prompts(self, temp_prompts_dir):
        """Test getting list of available prompts."""
        loader = PromptLoader(temp_prompts_dir)
        prompts = loader.get_available_prompts()
        
        assert len(prompts) == 1
        assert prompts[0]['name'] == 'test_analysis'
        assert prompts[0]['version'] == '1.0.0'
    
    def test_clear_cache(self, temp_prompts_dir):
        """Test cache clearing."""
        loader = PromptLoader(temp_prompts_dir)
        
        # Load prompt to populate cache
        loader.load_prompt('test_analysis')
        assert len(loader._cache) == 1
        
        # Clear cache
        loader.clear_cache()
        assert len(loader._cache) == 0
    
    def test_invalid_yaml_handling(self, temp_prompts_dir):
        """Test handling of invalid YAML files."""
        loader = PromptLoader(temp_prompts_dir)
        
        # Create invalid YAML file
        invalid_file = temp_prompts_dir / "invalid.yaml"
        with open(invalid_file, 'w') as f:
            f.write("invalid: yaml: content:")
        
        with pytest.raises(ValueError, match="Failed to load prompt"):
            loader.load_prompt('invalid')
    
    def test_missing_required_sections(self, temp_prompts_dir):
        """Test handling of YAML missing required sections."""
        loader = PromptLoader(temp_prompts_dir)
        
        # Create YAML without required sections
        incomplete_prompt = {'metadata': {'name': 'incomplete'}}
        incomplete_file = temp_prompts_dir / "incomplete.yaml"
        with open(incomplete_file, 'w') as f:
            yaml.dump(incomplete_prompt, f)
        
        with pytest.raises(ValueError, match="must contain 'prompts' section"):
            loader.load_prompt('incomplete')


class TestPromptVariableBuilder:
    """Test PromptVariableBuilder functionality."""
    
    def test_basic_variable_building(self):
        """Test basic variable addition."""
        builder = PromptVariableBuilder()
        variables = builder.add_variable('test_var', 'test_value').build()
        
        assert variables['test_var'] == 'test_value'
    
    def test_industry_context_building(self):
        """Test industry context variable building."""
        builder = PromptVariableBuilder()
        industry_config = {'key_skills': ['Python', 'JavaScript', 'React', 'AWS', 'Docker']}
        
        variables = builder.add_industry_context('tech_consulting', industry_config).build()
        
        assert variables['industry'] == 'tech_consulting'
        assert variables['industry_title'] == 'Tech Consulting'
        assert variables['industry_display'] == 'tech consulting'
        assert variables['industry_upper'] == 'TECH CONSULTING'
        assert 'Python, JavaScript, React, AWS, Docker' in variables['key_skills_list']
    
    def test_structure_context_building(self):
        """Test structure context building."""
        # Mock structure analysis
        class MockStructureAnalysis:
            def __init__(self):
                self.strengths = ['Clear formatting', 'Good organization', 'Professional tone']
        
        builder = PromptVariableBuilder()
        mock_analysis = MockStructureAnalysis()
        variables = builder.add_structure_context(mock_analysis).build()
        
        assert 'structure_context_section' in variables
        assert 'Clear formatting' in variables['structure_context_section']
    
    def test_structure_context_without_analysis(self):
        """Test structure context with no analysis."""
        builder = PromptVariableBuilder()
        variables = builder.add_structure_context(None).build()
        
        assert variables['structure_context_section'] == ""
    
    def test_chained_building(self):
        """Test chaining multiple builder methods."""
        variables = (PromptVariableBuilder()
                    .add_variable('resume_text', 'Sample resume')
                    .add_industry_context('finance_banking')
                    .build())
        
        assert 'resume_text' in variables
        assert 'industry' in variables
        assert 'industry_title' in variables


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_build_structure_variables(self):
        """Test structure variables builder function."""
        variables = build_structure_variables('Sample resume text')
        
        assert variables['resume_text'] == 'Sample resume text'
    
    def test_build_appeal_variables(self):
        """Test appeal variables builder function."""
        industry_config = {'key_skills': ['Finance', 'Analysis']}
        variables = build_appeal_variables(
            'Sample resume',
            'finance_banking',
            industry_config
        )
        
        assert 'resume_text' in variables
        assert 'industry' in variables
        assert 'key_skills_list' in variables


class TestRealPromptLoading:
    """Test loading real prompt files from the project."""
    
    def test_load_structure_prompt(self):
        """Test loading the real structure prompt."""
        try:
            loader = get_prompt_loader()
            prompt = loader.load_prompt('structure_analysis')
            
            assert prompt.name == 'structure_analysis'
            assert 'resume_text' in prompt.variables
            assert len(prompt.system_prompt) > 0
            assert len(prompt.user_prompt) > 0
            
        except FileNotFoundError:
            pytest.skip("Structure prompt file not found - may be running in different environment")
    
    def test_load_appeal_prompt(self):
        """Test loading the real appeal prompt."""
        try:
            loader = get_prompt_loader()
            prompt = loader.load_prompt('appeal_analysis', industry='tech_consulting')
            
            assert prompt.name == 'appeal_analysis'
            assert 'resume_text' in prompt.variables
            assert 'industry' in prompt.variables
            
        except FileNotFoundError:
            pytest.skip("Appeal prompt file not found - may be running in different environment")
    
    def test_prompt_substitution_compatibility(self):
        """Test that YAML prompts can substitute variables like hardcoded prompts."""
        try:
            loader = get_prompt_loader()
            prompt = loader.load_prompt('structure_analysis')
            
            # Test variable substitution
            substituted = prompt.substitute_variables(
                resume_text="John Doe\nSoftware Engineer\n• 5 years experience"
            )
            
            assert "John Doe" in substituted.user_prompt
            assert "Software Engineer" in substituted.user_prompt
            
        except FileNotFoundError:
            pytest.skip("Structure prompt file not found")


class TestPromptCompatibility:
    """Test compatibility between YAML prompts and hardcoded prompts."""
    
    def test_structure_prompt_output_format(self):
        """Test that structure prompt maintains expected output format."""
        try:
            loader = get_prompt_loader()
            prompt = loader.load_prompt('structure_analysis')
            
            substituted = prompt.substitute_variables(resume_text="Sample resume")
            
            # Check for expected sections in the prompt
            user_prompt = substituted.user_prompt.upper()
            expected_sections = [
                'FORMATTING ASSESSMENT',
                'SECTION ORGANIZATION',
                'PROFESSIONAL TONE',
                'COMPLETENESS',
                'FORMAT SCORE',
                'ORGANIZATION SCORE',
                'TONE SCORE',
                'COMPLETENESS SCORE'
            ]
            
            for section in expected_sections:
                assert section in user_prompt, f"Missing expected section: {section}"
                
        except FileNotFoundError:
            pytest.skip("Structure prompt file not found")
    
    def test_appeal_prompt_output_format(self):
        """Test that appeal prompt maintains expected output format."""
        try:
            loader = get_prompt_loader()
            prompt = loader.load_prompt('appeal_analysis')
            
            # Build variables like the legacy system would
            variables = build_appeal_variables(
                "Sample resume",
                "tech_consulting",
                {'key_skills': ['Python', 'AWS', 'React']}
            )
            
            substituted = prompt.substitute_variables(**variables)
            
            # Check for expected sections
            user_prompt = substituted.user_prompt.upper()
            expected_sections = [
                'ACHIEVEMENT RELEVANCE',
                'SKILLS ALIGNMENT', 
                'EXPERIENCE FIT',
                'COMPETITIVE POSITIONING',
                'RELEVANT ACHIEVEMENTS',
                'MISSING SKILLS',
                'MARKET TIER'
            ]
            
            for section in expected_sections:
                assert section in user_prompt, f"Missing expected section: {section}"
                
        except FileNotFoundError:
            pytest.skip("Appeal prompt file not found")


class TestGlobalFunctions:
    """Test global convenience functions."""
    
    def test_get_prompt_loader_singleton(self):
        """Test that get_prompt_loader returns the same instance."""
        loader1 = get_prompt_loader()
        loader2 = get_prompt_loader()
        
        assert loader1 is loader2  # Same instance
    
    def test_load_prompt_cached(self):
        """Test cached prompt loading function."""
        try:
            # This should work if prompts exist
            prompt1 = load_prompt_cached('structure_analysis')
            prompt2 = load_prompt_cached('structure_analysis')  # Should use cache
            
            assert prompt1.name == prompt2.name
            
        except FileNotFoundError:
            pytest.skip("Prompt files not found - testing in isolation")