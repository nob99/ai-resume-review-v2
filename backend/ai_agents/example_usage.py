"""Example usage of the AI agents for resume analysis.

This script demonstrates how to use the AI agents to analyze a resume.
NOTE: Requires OPENAI_API_KEY to be set in environment or .env file.
"""

import asyncio
import os
from typing import Dict, Any
from pprint import pprint

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.ai_agents import (
    ResumeAnalysisOrchestrator,
    validate_industry,
    validate_resume_text
)


# Sample resume for testing
SAMPLE_RESUME = """
John Doe
Senior Software Engineer
john.doe@email.com | (555) 123-4567 | LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe

PROFESSIONAL SUMMARY
Experienced software engineer with 8+ years developing scalable web applications and cloud-native solutions.
Expert in Python, JavaScript, and cloud technologies with a proven track record of leading technical initiatives
and mentoring development teams.

WORK EXPERIENCE

Senior Software Engineer | Tech Innovations Corp | San Francisco, CA | 2020-Present
• Led development of microservices architecture serving 5M+ daily active users
• Reduced API response time by 40% through optimization and caching strategies
• Mentored team of 8 junior developers, improving team velocity by 25%
• Implemented CI/CD pipeline reducing deployment time from 2 hours to 15 minutes
• Technologies: Python, FastAPI, React, AWS, Docker, Kubernetes, PostgreSQL

Software Engineer | StartupCo | San Francisco, CA | 2018-2020
• Built RESTful APIs using Python and FastAPI serving 100K+ users
• Developed React-based dashboard for real-time analytics visualization
• Collaborated with cross-functional teams in Agile/Scrum environment
• Improved test coverage from 45% to 85% using pytest and Jest
• Technologies: Python, Django, React, Node.js, MongoDB, Redis

Junior Software Engineer | Digital Solutions Inc | San Jose, CA | 2016-2018
• Developed features for e-commerce platform processing $10M+ in transactions
• Participated in code reviews and architectural design discussions
• Automated manual processes saving 20 hours per week
• Technologies: Java, Spring Boot, MySQL, Angular

EDUCATION

Bachelor of Science in Computer Science
University of California, Berkeley | 2016
GPA: 3.8/4.0 | Dean's List

TECHNICAL SKILLS

Programming: Python, JavaScript, TypeScript, Java, Go
Frameworks: FastAPI, Django, React, Node.js, Next.js, Spring Boot
Cloud & DevOps: AWS (EC2, S3, Lambda, RDS), Docker, Kubernetes, Jenkins, GitLab CI
Databases: PostgreSQL, MongoDB, Redis, MySQL, DynamoDB
Tools: Git, JIRA, Confluence, Datadog, New Relic

CERTIFICATIONS

• AWS Certified Solutions Architect - Associate (2022)
• Certified Kubernetes Administrator (CKA) (2021)

PROJECTS

Open Source Contributor
• Active contributor to FastAPI and React ecosystem
• Maintained popular Python package with 5K+ GitHub stars
• Presented at PyCon 2023 on "Building Scalable APIs with FastAPI"
"""


async def run_analysis_example():
    """Run a complete resume analysis example."""
    
    print("=" * 60)
    print("AI Resume Analysis Example")
    print("=" * 60)
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please set your OpenAI API key:")
        print("  export OPENAI_API_KEY='your-api-key-here'")
        return
    
    # Initialize orchestrator
    print("\n🚀 Initializing AI Resume Analysis Orchestrator...")
    orchestrator = ResumeAnalysisOrchestrator()
    
    # Industries to test
    industries = ["tech_consulting", "strategy_consulting"]
    
    for industry in industries:
        print(f"\n{'=' * 60}")
        print(f"Analyzing resume for: {industry.replace('_', ' ').title()}")
        print("=" * 60)
        
        try:
            # Validate inputs
            validated_industry = validate_industry(industry)
            validated_resume = validate_resume_text(SAMPLE_RESUME)
            
            print(f"\n⏳ Running analysis for {industry}...")
            print("   This may take 10-30 seconds...")
            
            # Run analysis
            result = await orchestrator.analyze(
                resume_text=validated_resume,
                industry=validated_industry
            )
            
            if result["success"]:
                print_analysis_results(result)
            else:
                print(f"\n❌ Analysis failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"\n❌ Error during analysis: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("=" * 60)


def print_analysis_results(result: Dict[str, Any]):
    """Pretty print analysis results."""
    
    print(f"\n✅ Analysis Successful!")
    print(f"   Analysis ID: {result['analysis_id']}")
    
    # Overall results
    print(f"\n📊 Overall Results:")
    print(f"   • Overall Score: {result['overall_score']}/100")
    print(f"   • Market Tier: {result['market_tier'].title()}")
    
    # Structure scores
    print(f"\n📋 Structure Analysis:")
    structure_scores = result['structure']['scores']
    for key, value in structure_scores.items():
        print(f"   • {key.replace('_', ' ').title()}: {value}/100")
    
    # Appeal scores
    print(f"\n🎯 Industry Appeal Analysis:")
    appeal_scores = result['appeal']['scores']
    for key, value in appeal_scores.items():
        print(f"   • {key.replace('_', ' ').title()}: {value}/100")
    
    # Key feedback
    print(f"\n💡 Key Feedback:")
    
    # Strengths
    strengths = result['structure']['feedback'].get('strengths', [])
    if strengths:
        print(f"   Strengths:")
        for strength in strengths[:3]:
            print(f"   • {strength}")
    
    # Areas for improvement
    improvements = result['appeal']['feedback'].get('improvement_areas', [])
    if improvements:
        print(f"   Areas for Improvement:")
        for improvement in improvements[:3]:
            print(f"   • {improvement}")
    
    # Missing skills
    missing_skills = result['appeal']['feedback'].get('missing_skills', [])
    if missing_skills:
        print(f"   Missing Skills:")
        for skill in missing_skills[:3]:
            print(f"   • {skill}")
    
    # Summary
    print(f"\n📝 Summary:")
    summary_lines = result['summary'].split('. ')
    for line in summary_lines:
        if line.strip():
            print(f"   {line.strip()}{'.' if not line.endswith('.') else ''}")


def main():
    """Main entry point."""
    try:
        # Run the async analysis
        asyncio.run(run_analysis_example())
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()