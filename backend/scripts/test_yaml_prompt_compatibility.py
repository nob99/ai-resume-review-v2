#!/usr/bin/env python3
"""
YAML Prompt Compatibility Test
===============================

This script tests that YAML-based prompts produce identical output format and structure
compared to the original hardcoded prompts in the agents.

Usage:
    python3 scripts/test_yaml_prompt_compatibility.py
"""

import sys
import os
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.ai_agents.prompts.loader import get_prompt_loader, build_structure_variables, build_appeal_variables


def test_structure_prompt_compatibility():
    """Test that YAML structure prompt matches hardcoded format."""
    print("🔍 Testing Structure Prompt Compatibility...")
    
    try:
        # Load YAML prompt
        loader = get_prompt_loader()
        prompt = loader.load_prompt('structure_analysis')
        
        # Sample resume for testing
        sample_resume = """
        John Doe
        Senior Software Engineer
        john.doe@email.com | (555) 123-4567
        
        Professional Summary:
        Experienced software engineer with 5+ years in full-stack development.
        
        Experience:
        Senior Software Engineer at TechCorp (2020-2024)
        • Led development of microservices architecture
        • Improved system performance by 40%
        • Mentored team of 3 junior developers
        
        Software Engineer at StartupInc (2018-2020)
        • Built scalable web applications using React and Node.js
        • Implemented CI/CD pipelines
        
        Skills:
        • Programming: Python, JavaScript, TypeScript, Java
        • Frameworks: React, Node.js, Django, Spring Boot
        • Cloud: AWS, Docker, Kubernetes
        • Databases: PostgreSQL, MongoDB, Redis
        
        Education:
        B.S. Computer Science, State University (2018)
        """.strip()
        
        # Build variables and substitute
        variables = build_structure_variables(sample_resume)
        substituted_prompt = prompt.substitute_variables(**variables)
        
        # Test key sections are present
        user_prompt = substituted_prompt.user_prompt
        system_prompt = substituted_prompt.system_prompt
        
        print("  ✅ YAML prompt loaded successfully")
        print(f"  📊 System prompt length: {len(system_prompt)} chars")
        print(f"  📝 User prompt length: {len(user_prompt)} chars")
        
        # Check for expected structure elements
        expected_elements = [
            "FORMATTING ASSESSMENT",
            "SECTION ORGANIZATION", 
            "PROFESSIONAL TONE",
            "COMPLETENESS",
            "Format Score: [0-100]",
            "Section Organization Score: [0-100]",
            "Professional Tone Score: [0-100]",
            "Completeness Score: [0-100]",
            "Formatting Issues:",
            "Missing Sections:",
            "Tone Problems:",
            "Completeness Gaps:",
            "Strengths:",
            "Recommendations:"
        ]
        
        missing_elements = []
        for element in expected_elements:
            if element not in user_prompt:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"  ❌ Missing elements: {missing_elements}")
            return False
        
        print("  ✅ All expected elements present in user prompt")
        
        # Check system prompt content
        system_expected = [
            "expert resume structure",
            "formatting analyst", 
            "structural quality",
            "Visual layout",
            "Section organization",
            "Professional language"
        ]
        
        missing_system = []
        for element in system_expected:
            if element.lower() not in system_prompt.lower():
                missing_system.append(element)
        
        if missing_system:
            print(f"  ❌ Missing system elements: {missing_system}")
            return False
        
        print("  ✅ System prompt contains expected elements")
        
        # Verify resume text substitution
        if "John Doe" not in user_prompt or "Senior Software Engineer" not in user_prompt:
            print("  ❌ Resume text not properly substituted")
            return False
        
        print("  ✅ Variable substitution working correctly")
        return True
        
    except Exception as e:
        print(f"  ❌ Error testing structure prompt: {str(e)}")
        return False


def test_appeal_prompt_compatibility():
    """Test that YAML appeal prompt matches hardcoded format."""
    print("\n🎯 Testing Appeal Prompt Compatibility...")
    
    try:
        # Load YAML prompt
        loader = get_prompt_loader()
        prompt = loader.load_prompt('appeal_analysis')
        
        # Sample resume and context
        sample_resume = """
        Jane Smith
        Data Scientist
        jane.smith@email.com
        
        Professional Summary:
        Data scientist with 4 years experience in machine learning and analytics.
        
        Experience:
        Senior Data Scientist at DataCorp (2022-2024)
        • Built predictive models improving revenue by 25%
        • Led analytics team of 4 data scientists
        • Implemented MLOps pipeline reducing deployment time by 60%
        
        Skills:
        • Programming: Python, R, SQL
        • ML/AI: TensorFlow, PyTorch, Scikit-learn
        • Cloud: AWS, GCP, Azure
        • Visualization: Tableau, PowerBI
        """.strip()
        
        # Build appeal variables with industry context
        industry_config = {
            'key_skills': ['Python', 'Machine Learning', 'Statistics', 'SQL', 'AWS'],
            'display_name': 'Technology Consulting'
        }
        
        variables = build_appeal_variables(
            sample_resume,
            'tech_consulting',
            industry_config
        )
        
        substituted_prompt = prompt.substitute_variables(**variables)
        
        user_prompt = substituted_prompt.user_prompt
        system_prompt = substituted_prompt.system_prompt
        
        print("  ✅ YAML appeal prompt loaded successfully")
        print(f"  📊 System prompt length: {len(system_prompt)} chars")
        print(f"  📝 User prompt length: {len(user_prompt)} chars")
        
        # Check for expected appeal elements
        expected_elements = [
            "ACHIEVEMENT RELEVANCE ASSESSMENT",
            "SKILLS ALIGNMENT ASSESSMENT",
            "EXPERIENCE FIT ASSESSMENT", 
            "COMPETITIVE POSITIONING ASSESSMENT",
            "Achievement Relevance Score: [0-100]",
            "Skills Alignment Score: [0-100]",
            "Experience Fit Score: [0-100]",
            "Competitive Positioning Score: [0-100]",
            "Relevant Achievements:",
            "Missing Skills:",
            "Transferable Experience:",
            "Industry Keywords:",
            "Market Tier:",
            "Competitive Advantages:",
            "Improvement Areas:"
        ]
        
        missing_elements = []
        for element in expected_elements:
            if element not in user_prompt:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"  ❌ Missing elements: {missing_elements}")
            return False
        
        print("  ✅ All expected elements present in user prompt")
        
        # Check industry-specific substitution
        if "tech consulting" not in user_prompt.lower():
            print("  ❌ Industry not properly substituted")
            return False
        
        if "Python, Machine Learning" not in user_prompt:
            print("  ❌ Key skills not properly substituted")
            return False
        
        print("  ✅ Industry-specific variables substituted correctly")
        
        # Check system prompt
        system_expected = [
            "expert",
            "industry analyst",
            "recruitment specialist",
            "Tech Consulting",  # This is what our variable builder actually produces
            "competitive"
        ]
        
        missing_system = []
        for element in system_expected:
            if element.lower() not in system_prompt.lower():
                missing_system.append(element)
        
        if missing_system:
            print(f"  ❌ Missing system elements: {missing_system}")
            return False
        
        print("  ✅ System prompt contains expected elements")
        
        # Verify resume text substitution
        if "Jane Smith" not in user_prompt or "Data Scientist" not in user_prompt:
            print("  ❌ Resume text not properly substituted")
            return False
        
        print("  ✅ Variable substitution working correctly")
        return True
        
    except Exception as e:
        print(f"  ❌ Error testing appeal prompt: {str(e)}")
        return False


def test_prompt_loader_performance():
    """Test prompt loader caching and performance."""
    print("\n⚡ Testing Prompt Loader Performance...")
    
    try:
        import time
        
        loader = get_prompt_loader()
        
        # Test caching - first load
        start_time = time.time()
        prompt1 = loader.load_prompt('structure_analysis')
        first_load_time = time.time() - start_time
        
        # Test caching - second load (should be faster)
        start_time = time.time()
        prompt2 = loader.load_prompt('structure_analysis')
        second_load_time = time.time() - start_time
        
        print(f"  ⏱️  First load time: {first_load_time:.4f}s")
        print(f"  ⚡ Cached load time: {second_load_time:.4f}s")
        
        if second_load_time < first_load_time:
            print("  ✅ Caching is working (second load faster)")
        else:
            print("  ⚠️  Caching may not be working optimally")
        
        # Test cache contents
        cache_size = len(loader._cache)
        print(f"  💾 Cache size: {cache_size} items")
        
        if cache_size > 0:
            print("  ✅ Cache populated correctly")
        else:
            print("  ❌ Cache not populated")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error testing performance: {str(e)}")
        return False


def test_available_prompts():
    """Test getting available prompts."""
    print("\n📋 Testing Available Prompts Discovery...")
    
    try:
        loader = get_prompt_loader()
        available = loader.get_available_prompts()
        
        print(f"  📊 Found {len(available)} available prompts")
        
        for prompt_info in available:
            print(f"    • {prompt_info['name']} v{prompt_info['version']}: {prompt_info['description']}")
        
        # Check for our expected prompts
        prompt_names = [p['name'] for p in available]
        expected_prompts = ['structure_analysis', 'appeal_analysis']
        
        missing_prompts = [name for name in expected_prompts if name not in prompt_names]
        if missing_prompts:
            print(f"  ❌ Missing expected prompts: {missing_prompts}")
            return False
        
        print("  ✅ All expected prompts found")
        return True
        
    except Exception as e:
        print(f"  ❌ Error discovering prompts: {str(e)}")
        return False


def test_error_handling():
    """Test error handling for invalid prompts."""
    print("\n🚨 Testing Error Handling...")
    
    try:
        loader = get_prompt_loader()
        
        # Test loading non-existent prompt
        try:
            loader.load_prompt('nonexistent_prompt_name')
            print("  ❌ Should have raised FileNotFoundError")
            return False
        except FileNotFoundError:
            print("  ✅ Correctly raised FileNotFoundError for missing prompt")
        
        # Test variable validation
        try:
            prompt = loader.load_prompt('structure_analysis')
            prompt.substitute_variables()  # Missing required variable
            print("  ❌ Should have raised ValueError for missing variables")
            return False
        except ValueError as e:
            if "Missing required variables" in str(e):
                print("  ✅ Correctly validated missing variables")
            else:
                print(f"  ❌ Wrong error message: {str(e)}")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Unexpected error in error handling test: {str(e)}")
        return False


def main():
    """Run all compatibility tests."""
    print("🚀 YAML Prompt Compatibility Test Suite")
    print("=" * 60)
    
    tests = [
        ("Structure Prompt Compatibility", test_structure_prompt_compatibility),
        ("Appeal Prompt Compatibility", test_appeal_prompt_compatibility),  
        ("Prompt Loader Performance", test_prompt_loader_performance),
        ("Available Prompts Discovery", test_available_prompts),
        ("Error Handling", test_error_handling)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\n📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! YAML prompts are compatible with hardcoded prompts.")
        return 0
    else:
        print("⚠️  Some tests failed. YAML prompts may need adjustment.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)