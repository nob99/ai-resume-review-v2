"""
Prompt Loader for AI Agents
============================

This module handles loading and caching of YAML-based prompts for AI agents.
It provides a clean interface for prompt management with versioning, caching,
and variable substitution capabilities.

Key Features:
- YAML-based prompt configuration
- In-memory caching for performance  
- Variable substitution with validation
- Version management and A/B testing support
- Industry-specific prompt variations
"""

import os
import re
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from functools import lru_cache

from app.ai_agents.interface import PromptTemplate

logger = logging.getLogger(__name__)


@dataclass
class LoadedPrompt:
    """Container for a loaded prompt with all metadata."""
    
    name: str
    version: str
    description: str
    system_prompt: str
    user_prompt: str
    variables: List[str]
    metadata: Dict[str, Any]
    output_parsing: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    tags: List[str] = None
    
    def substitute_variables(self, **kwargs) -> 'LoadedPrompt':
        """Create a new LoadedPrompt with variables substituted."""
        # Validate required variables
        missing_vars = [var for var in self.variables if var not in kwargs]
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        
        # Perform substitution
        system_prompt = self.system_prompt.format(**kwargs) if self.system_prompt else ""
        user_prompt = self.user_prompt.format(**kwargs) if self.user_prompt else ""
        
        return LoadedPrompt(
            name=self.name,
            version=self.version, 
            description=self.description,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            variables=self.variables,
            metadata=self.metadata,
            output_parsing=self.output_parsing,
            validation=self.validation,
            tags=self.tags or []
        )


class PromptLoader:
    """
    Loads and manages YAML-based prompts with caching and variable substitution.
    
    This class provides a centralized way to load AI prompts from YAML files,
    with support for caching, versioning, and dynamic variable substitution.
    """
    
    def __init__(self, prompts_dir: Optional[Union[str, Path]] = None):
        """
        Initialize the prompt loader.
        
        Args:
            prompts_dir: Directory containing prompt YAML files.
                        Defaults to app/ai_agents/prompts/templates/
        """
        if prompts_dir is None:
            # Default to templates directory relative to this file
            current_dir = Path(__file__).parent
            prompts_dir = current_dir / "templates"
        
        self.prompts_dir = Path(prompts_dir)
        self._cache = {}  # Simple in-memory cache
        
        if not self.prompts_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")
        
        logger.info(f"PromptLoader initialized with directory: {self.prompts_dir}")
    
    def load_prompt(
        self,
        prompt_name: str,
        version: Optional[str] = None,
        industry: Optional[str] = None
    ) -> LoadedPrompt:
        """
        Load a prompt by name and optionally version.
        
        Args:
            prompt_name: Name of the prompt (e.g., 'structure_analysis', 'appeal_analysis')
            version: Specific version to load (defaults to latest)
            industry: Industry context for industry-specific prompts
            
        Returns:
            LoadedPrompt: Loaded prompt with metadata
            
        Raises:
            FileNotFoundError: If prompt file doesn't exist
            ValueError: If YAML is invalid or missing required fields
        """
        # Generate cache key
        cache_key = f"{prompt_name}:{version or 'latest'}:{industry or 'default'}"
        
        # Check cache first
        if cache_key in self._cache:
            logger.debug(f"Loading prompt from cache: {cache_key}")
            return self._cache[cache_key]
        
        # Find the prompt file
        prompt_file = self._find_prompt_file(prompt_name, version)
        if not prompt_file:
            raise FileNotFoundError(f"Prompt not found: {prompt_name} (version: {version})")
        
        # Load and parse YAML
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = yaml.safe_load(f)
            
            loaded_prompt = self._parse_prompt_data(prompt_data, industry)
            
            # Cache the result
            self._cache[cache_key] = loaded_prompt
            logger.info(f"Loaded prompt: {prompt_name} v{loaded_prompt.version}")
            
            return loaded_prompt
            
        except Exception as e:
            logger.error(f"Error loading prompt {prompt_name}: {str(e)}")
            raise ValueError(f"Failed to load prompt {prompt_name}: {str(e)}")
    
    def get_available_prompts(self) -> List[Dict[str, Any]]:
        """
        Get list of all available prompts with their metadata.
        
        Returns:
            List of prompt info dictionaries
        """
        prompts = []
        
        # Scan all YAML files in prompts directory
        for yaml_file in self.prompts_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    
                if 'metadata' in data:
                    metadata = data['metadata']
                    prompts.append({
                        'name': metadata.get('name', yaml_file.stem),
                        'version': metadata.get('version', '1.0.0'),
                        'description': metadata.get('description', ''),
                        'agent_type': metadata.get('agent_type', ''),
                        'file_path': str(yaml_file),
                        'industry_specific': metadata.get('industry_specific', False)
                    })
                        
            except Exception as e:
                logger.warning(f"Could not parse prompt file {yaml_file}: {str(e)}")
        
        return sorted(prompts, key=lambda x: (x['name'], x['version']))
    
    def clear_cache(self):
        """Clear the prompt cache."""
        self._cache.clear()
        logger.info("Prompt cache cleared")
    
    def _find_prompt_file(self, prompt_name: str, version: Optional[str] = None) -> Optional[Path]:
        """Find the appropriate prompt file."""
        # Try different patterns to match our file naming
        patterns_to_try = []
        
        if version:
            # Look for specific version patterns
            patterns_to_try.extend([
                f"*{prompt_name}*v{version}*.yaml",
                f"{prompt_name}_v{version}.yaml",
                f"*{prompt_name}*{version}*.yaml"
            ])
        
        # Always try general patterns - also try converting underscores
        name_variants = [prompt_name]
        if '_' in prompt_name:
            # Try without the suffix (structure_analysis -> structure)
            name_variants.append(prompt_name.split('_')[0])
        
        for name_variant in name_variants:
            patterns_to_try.extend([
                f"{name_variant}_v*.yaml",  # structure_v1.yaml, appeal_v1.yaml
                f"*{name_variant}*.yaml",   # any file containing the name
                f"{name_variant}.yaml"      # exact match
            ])
        
        # Try each pattern
        for pattern in patterns_to_try:
            matching_files = list(self.prompts_dir.rglob(pattern))
            if matching_files:
                # If multiple matches, prefer the one with highest version
                if len(matching_files) > 1:
                    # Sort by version (simple string sort should work for semantic versioning)
                    matching_files.sort(key=lambda f: f.name, reverse=True)
                return matching_files[0]
        
        return None
    
    def _parse_prompt_data(self, data: Dict[str, Any], industry: Optional[str] = None) -> LoadedPrompt:
        """Parse YAML prompt data into LoadedPrompt object."""
        if 'metadata' not in data:
            raise ValueError("Prompt YAML must contain 'metadata' section")
        
        if 'prompts' not in data:
            raise ValueError("Prompt YAML must contain 'prompts' section")
        
        metadata = data['metadata']
        prompts = data['prompts']
        
        # Extract basic information
        name = metadata.get('name', '')
        version = metadata.get('version', '1.0.0')
        description = metadata.get('description', '')
        
        # Extract prompts
        system_prompt = prompts.get('system', '')
        user_prompt = prompts.get('user', '')
        
        # Extract variables
        variables_section = data.get('variables', [])
        if isinstance(variables_section, list):
            # New format: list of variable objects
            variables = []
            for var in variables_section:
                if isinstance(var, dict):
                    variables.append(var.get('name', ''))
                elif isinstance(var, str):
                    variables.append(var)
        else:
            # Legacy format: simple list
            variables = variables_section
        
        # Apply industry-specific configurations if available
        if industry and 'industry_configs' in data:
            industry_config = data['industry_configs'].get(industry, {})
            if industry_config:
                # Add industry-specific variables to metadata
                metadata['industry_config'] = industry_config
        
        return LoadedPrompt(
            name=name,
            version=version,
            description=description,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            variables=variables,
            metadata=metadata,
            output_parsing=data.get('output_parsing'),
            validation=data.get('validation'),
            tags=data.get('tags', [])
        )


# Global prompt loader instance (initialized lazily)
_global_prompt_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Get the global prompt loader instance."""
    global _global_prompt_loader
    if _global_prompt_loader is None:
        _global_prompt_loader = PromptLoader()
    return _global_prompt_loader


@lru_cache(maxsize=128)
def load_prompt_cached(
    prompt_name: str,
    version: Optional[str] = None,
    industry: Optional[str] = None
) -> LoadedPrompt:
    """
    Load a prompt with LRU caching.
    
    This is a convenience function that provides an additional layer of caching
    using functools.lru_cache for frequently accessed prompts.
    """
    loader = get_prompt_loader()
    return loader.load_prompt(prompt_name, version, industry)


class PromptVariableBuilder:
    """Helper class for building prompt variables dynamically."""
    
    def __init__(self):
        self.variables = {}
    
    def add_variable(self, name: str, value: Any) -> 'PromptVariableBuilder':
        """Add a variable to the builder."""
        self.variables[name] = value
        return self
    
    def add_industry_context(self, industry: str, industry_config: Optional[Dict] = None) -> 'PromptVariableBuilder':
        """Add industry-related variables."""
        # Format industry name in different ways
        self.variables['industry'] = industry
        self.variables['industry_title'] = industry.replace('_', ' ').title()
        self.variables['industry_display'] = industry.replace('_', ' ')
        self.variables['industry_upper'] = industry.replace('_', ' ').upper()
        
        # Add industry configuration if provided
        if industry_config:
            key_skills = industry_config.get('key_skills', [])
            self.variables['key_skills_list'] = ', '.join(key_skills[:5])  # Top 5 skills
        
        return self
    
    def add_structure_context(self, structure_analysis=None) -> 'PromptVariableBuilder':
        """Add structure analysis context."""
        if structure_analysis:
            strengths = getattr(structure_analysis, 'strengths', [])
            context_text = f"""
STRUCTURE ANALYSIS CONTEXT:
The resume has been analyzed for structure with the following insights:
- Key Strengths: {', '.join(strengths[:3])}
- Areas for improvement have been identified and should inform your analysis
- Use this context to provide more targeted industry-specific feedback

"""
            self.variables['structure_context_section'] = context_text
        else:
            self.variables['structure_context_section'] = ""
        
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build the final variables dictionary."""
        return self.variables.copy()


# Convenience functions
def build_structure_variables(resume_text: str) -> Dict[str, Any]:
    """Build variables for structure analysis prompt."""
    return PromptVariableBuilder().add_variable('resume_text', resume_text).build()


def build_appeal_variables(
    resume_text: str,
    industry: str,
    industry_config: Optional[Dict] = None,
    structure_analysis=None
) -> Dict[str, Any]:
    """Build variables for appeal analysis prompt."""
    return (PromptVariableBuilder()
            .add_variable('resume_text', resume_text)
            .add_industry_context(industry, industry_config)
            .add_structure_context(structure_analysis)
            .build())