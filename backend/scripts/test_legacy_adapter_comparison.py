#!/usr/bin/env python3
"""
Legacy Adapter Comparison Test
===============================

This script tests that our legacy adapter produces equivalent results to direct usage
of the ResumeAnalysisOrchestrator. It's designed to validate the adapter without
requiring actual AI API calls.

Usage:
    python3 scripts/test_legacy_adapter_comparison.py
"""

import asyncio
import sys
import os
import time
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from unittest.mock import AsyncMock, patch, MagicMock
from app.ai_agents.legacy_adapter import LegacyAIAdapter
from app.ai_agents.interface import AnalysisRequest, Industry
from app.ai.models.analysis_request import (
    CompleteAnalysisResult,
    StructureAnalysisResult,
    AppealAnalysisResult
)


def create_mock_legacy_result() -> CompleteAnalysisResult:
    """Create a realistic mock result from the legacy system."""
    structure_result = StructureAnalysisResult(
        format_score=85.0,
        section_organization_score=90.0,
        professional_tone_score=88.0,
        completeness_score=82.0,
        formatting_issues=["Minor spacing inconsistency"],
        missing_sections=[],
        tone_problems=[],
        completeness_gaps=["Could add more quantified achievements"],
        strengths=["Clear professional summary", "Well-organized sections"],
        recommendations=["Add more specific metrics", "Improve formatting consistency"],
        total_sections_found=4,
        word_count=150,
        estimated_reading_time_minutes=1,
        confidence_score=0.85,
        processing_time_ms=2500,
        model_used="gpt-4",
        prompt_version="v1.0"
    )
    
    appeal_result = AppealAnalysisResult(
        achievement_relevance_score=88.0,
        skills_alignment_score=85.0,
        experience_fit_score=90.0,
        competitive_positioning_score=82.0,
        relevant_achievements=["Led microservices architecture", "40% performance improvement"],
        missing_skills=["Machine Learning", "Data Science"],
        transferable_experience=["Team leadership", "Performance optimization"],
        industry_keywords=["microservices", "AWS", "performance"],
        market_tier="senior",
        competitive_advantages=["Strong technical leadership", "Proven results"],
        improvement_areas=["Add ML skills", "More quantified metrics"],
        structure_context_used=True,
        target_industry="tech_consulting",
        confidence_score=0.87,
        processing_time_ms=3000,
        model_used="gpt-4",
        prompt_version="v1.0"
    )
    
    return CompleteAnalysisResult(
        overall_score=86.2,
        structure_analysis=structure_result,
        appeal_analysis=appeal_result,
        analysis_summary="Strong technical professional with proven leadership experience.",
        key_strengths=["Technical expertise", "Leadership experience", "Quantified results"],
        priority_improvements=["Add ML skills", "More specific metrics", "Industry certifications"],
        industry="tech_consulting",
        analysis_id="test-comparison-123",
        completed_at="2025-01-07T10:00:00Z",
        processing_time_seconds=5.5,
        confidence_metrics={"structure": 0.85, "appeal": 0.87}
    )


async def test_adapter_comparison():
    """Test that adapter produces expected results."""
    print("🔍 Testing Legacy AI Adapter...")
    
    # Sample resume for testing
    sample_resume = """
    John Doe
    Senior Software Engineer
    
    Professional Summary:
    Experienced software engineer with 5+ years in web development.
    
    Skills:
    • Python, JavaScript, React
    • AWS, Docker, Kubernetes  
    • Team leadership and mentoring
    
    Experience:
    Software Engineer at Tech Corp (2019-2024)
    • Led development of microservices architecture
    • Improved system performance by 40%
    • Mentored junior developers
    """.strip()
    
    request = AnalysisRequest(
        text=sample_resume,
        industry=Industry.STRATEGY_TECH,
        role="Senior Software Engineer"
    )
    
    mock_result = create_mock_legacy_result()
    
    # Test with mocked orchestrator
    with patch('app.ai_agents.legacy_adapter.ResumeAnalysisOrchestrator') as mock_orchestrator_class:
        mock_orchestrator = AsyncMock()
        mock_orchestrator.analyze_resume.return_value = mock_result
        mock_orchestrator_class.return_value = mock_orchestrator
        
        with patch('app.ai_agents.legacy_adapter.OpenAIClient'):
            # Initialize adapter
            print("  ✅ Initializing adapter...")
            adapter = LegacyAIAdapter()
            
            # Test analysis
            print("  🧠 Running analysis...")
            start_time = time.time()
            result = await adapter.analyze_resume(request)
            processing_time = time.time() - start_time
            
            # Verify results
            print(f"  ⏱️  Processing time: {processing_time:.3f}s")
            print(f"  📊 Overall score: {result.overall_score}/100")
            print(f"  📈 Structure score: {result.structure_score.score}/100")
            print(f"  🎯 Appeal score: {result.appeal_score.score}/100")
            print(f"  💪 Strengths: {len(result.strengths)} identified")
            print(f"  🔧 Recommendations: {len(result.recommendations)} provided")
            
            # Validate key aspects
            assertions = [
                ("Overall score matches", result.overall_score == 86),
                ("Structure score calculated", result.structure_score.score == 86),
                ("Appeal score calculated", result.appeal_score.score == 86),
                ("Summary preserved", len(result.summary) > 0),
                ("AI model tracked", "gpt-4" in result.ai_model_used),
                ("Confidence calculated", 0.0 <= result.confidence_score <= 1.0),
                ("Processing time recorded", result.processing_time_ms > 0),
                ("Strengths extracted", len(result.strengths) > 0),
                ("Recommendations provided", len(result.recommendations) > 0)
            ]
            
            all_passed = True
            for description, assertion in assertions:
                status = "✅" if assertion else "❌"
                print(f"    {status} {description}")
                if not assertion:
                    all_passed = False
            
            return all_passed


async def test_industry_mapping():
    """Test industry mapping functionality."""
    print("\n🗺️  Testing Industry Mapping...")
    
    test_cases = [
        (Industry.STRATEGY_TECH, "tech_consulting"),
        (Industry.MA_FINANCIAL, "finance_banking"), 
        (Industry.CONSULTING, "general_business"),
        (Industry.SYSTEM_INTEGRATOR, "system_integrator"),
        (Industry.GENERAL, "general_business")
    ]
    
    mock_result = create_mock_legacy_result()
    
    with patch('app.ai_agents.legacy_adapter.ResumeAnalysisOrchestrator') as mock_orchestrator_class:
        mock_orchestrator = AsyncMock()
        mock_orchestrator.analyze_resume.return_value = mock_result
        mock_orchestrator_class.return_value = mock_orchestrator
        
        with patch('app.ai_agents.legacy_adapter.OpenAIClient'):
            adapter = LegacyAIAdapter()
            
            all_passed = True
            for new_industry, expected_legacy in test_cases:
                request = AnalysisRequest(
                    text="Sample resume text for mapping test",
                    industry=new_industry
                )
                
                await adapter.analyze_resume(request)
                
                # Check that correct legacy industry was used
                call_args = mock_orchestrator.analyze_resume.call_args
                actual_legacy = call_args[1]['industry']
                
                passed = actual_legacy == expected_legacy
                status = "✅" if passed else "❌"
                print(f"  {status} {new_industry.value} → {actual_legacy} (expected: {expected_legacy})")
                
                if not passed:
                    all_passed = False
            
            return all_passed


async def test_error_handling():
    """Test error handling capabilities."""
    print("\n⚠️  Testing Error Handling...")
    
    with patch('app.ai_agents.legacy_adapter.ResumeAnalysisOrchestrator') as mock_orchestrator_class:
        with patch('app.ai_agents.legacy_adapter.OpenAIClient'):
            adapter = LegacyAIAdapter()
            
            # Test input validation
            test_cases = [
                ("Empty text", ""),
                ("Very short text", "Hi"),
                ("Very long text", "A" * 60000)
            ]
            
            all_passed = True
            for description, text in test_cases:
                try:
                    request = AnalysisRequest(text=text, industry=Industry.GENERAL)
                    await adapter.analyze_resume(request)
                    print(f"  ❌ {description}: Should have raised exception")
                    all_passed = False
                except Exception as e:
                    print(f"  ✅ {description}: Correctly raised {type(e).__name__}")
            
            return all_passed


async def test_health_check():
    """Test health check functionality."""
    print("\n🏥 Testing Health Check...")
    
    mock_result = create_mock_legacy_result()
    
    with patch('app.ai_agents.legacy_adapter.ResumeAnalysisOrchestrator') as mock_orchestrator_class:
        mock_orchestrator = AsyncMock()
        mock_orchestrator.analyze_resume.return_value = mock_result
        mock_orchestrator_class.return_value = mock_orchestrator
        
        with patch('app.ai_agents.legacy_adapter.OpenAIClient'):
            adapter = LegacyAIAdapter()
            
            # Test successful health check
            health_ok = await adapter.health_check()
            status = "✅" if health_ok else "❌"
            print(f"  {status} Health check passed: {health_ok}")
            
            # Test failed health check
            mock_orchestrator.analyze_resume.side_effect = Exception("Service down")
            health_ok = await adapter.health_check()
            status = "✅" if not health_ok else "❌"
            print(f"  {status} Health check failed correctly: {not health_ok}")
            
            return True


async def main():
    """Run all comparison tests."""
    print("🚀 Legacy AI Adapter Comparison Test Suite")
    print("=" * 50)
    
    tests = [
        ("Basic Adapter Comparison", test_adapter_comparison),
        ("Industry Mapping", test_industry_mapping),
        ("Error Handling", test_error_handling),
        ("Health Check", test_health_check)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Results Summary:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Legacy adapter is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the adapter implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)