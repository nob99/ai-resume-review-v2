"""Pytest configuration and fixtures for AI agents tests."""

import pytest
from unittest.mock import AsyncMock, Mock
from typing import Dict, Any


@pytest.fixture
def sample_resume_text():
    """Sample resume text for testing."""
    return """
    John Doe
    Software Engineer
    john.doe@email.com | (555) 123-4567 | LinkedIn: linkedin.com/in/johndoe
    
    PROFESSIONAL SUMMARY
    Experienced software engineer with 5+ years developing scalable web applications.
    Proficient in Python, JavaScript, and cloud technologies.
    
    WORK EXPERIENCE
    Senior Software Engineer | Tech Corp | 2020-Present
    - Led development of microservices architecture serving 1M+ users
    - Reduced API response time by 40% through optimization
    - Mentored team of 5 junior developers
    
    Software Engineer | StartupCo | 2018-2020
    - Built RESTful APIs using Python and FastAPI
    - Implemented CI/CD pipeline reducing deployment time by 60%
    - Collaborated with cross-functional teams in Agile environment
    
    EDUCATION
    Bachelor of Science in Computer Science
    University of Technology | 2018
    
    SKILLS
    Programming: Python, JavaScript, TypeScript, Java
    Frameworks: FastAPI, React, Node.js, Django
    Cloud: AWS, Docker, Kubernetes
    Databases: PostgreSQL, MongoDB, Redis
    """


@pytest.fixture
def mock_openai_structure_response():
    """Mock OpenAI response for structure analysis."""
    return """
    SCORES:
    - Format Score: 85
    - Section Organization Score: 90
    - Professional Tone Score: 88
    - Completeness Score: 82
    
    STRUCTURAL ANALYSIS:
    
    Formatting Issues:
    - Inconsistent spacing between sections
    - Missing dates for education
    
    Missing Sections:
    - No certifications section
    - No projects section
    
    Tone Problems:
    - None identified - professional tone throughout
    
    Completeness Gaps:
    - Could include more quantifiable achievements
    - Missing information about team size at current role
    
    Strengths:
    - Clear section headers
    - Professional summary is concise and effective
    - Good use of bullet points
    - Quantifiable achievements included
    
    Recommendations:
    - Add a certifications section if applicable
    - Include personal projects to showcase skills
    - Ensure consistent spacing throughout document
    - Add more metrics to achievements
    
    METADATA:
    - Total Sections Found: 5
    - Word Count: 250
    - Estimated Reading Time: 2
    """


@pytest.fixture
def mock_openai_appeal_response():
    """Mock OpenAI response for appeal analysis."""
    return """
    SCORES:
    - Achievement Relevance Score: 88
    - Skills Alignment Score: 92
    - Experience Fit Score: 85
    - Competitive Positioning Score: 87
    
    DETAILED INDUSTRY ANALYSIS:
    
    Relevant Achievements:
    - Led development of microservices architecture serving 1M+ users
    - Reduced API response time by 40% through optimization
    - Implemented CI/CD pipeline reducing deployment time by 60%
    
    Missing Skills:
    - Cloud architecture certification
    - Experience with Terraform or IaC tools
    - Knowledge of service mesh technologies
    
    Transferable Experience:
    - Strong API development background
    - Team leadership and mentoring
    - Performance optimization expertise
    
    Industry Keywords:
    - Microservices, API, Cloud, Docker, Kubernetes
    - Missing: DevOps, IaC, Service Mesh
    
    COMPETITIVE ASSESSMENT:
    
    Market Tier: senior
    
    Competitive Advantages:
    - Proven track record with large-scale systems
    - Strong technical leadership experience
    - Full-stack capabilities with modern tech stack
    
    Improvement Areas:
    - Add cloud certifications (AWS Solutions Architect)
    - Include more DevOps and infrastructure experience
    - Highlight experience with specific industry verticals
    """


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_structure_agent(mock_openai_client, mock_openai_structure_response):
    """Mock structure agent."""
    from app.ai_agents.agents.structure import StructureAgent
    
    agent = StructureAgent()
    agent.client = mock_openai_client
    
    # Mock the OpenAI response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = mock_openai_structure_response
    
    agent.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    return agent


@pytest.fixture
def mock_appeal_agent(mock_openai_client, mock_openai_appeal_response):
    """Mock appeal agent."""
    from app.ai_agents.agents.appeal import AppealAgent
    
    agent = AppealAgent()
    agent.client = mock_openai_client
    
    # Mock the OpenAI response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = mock_openai_appeal_response
    
    agent.client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    return agent


@pytest.fixture
def initial_state(sample_resume_text):
    """Initial state for workflow testing."""
    return {
        "resume_text": sample_resume_text,
        "industry": "tech_consulting",
        "structure_scores": None,
        "structure_feedback": None,
        "structure_metadata": None,
        "appeal_scores": None,
        "appeal_feedback": None,
        "market_tier": None,
        "overall_score": None,
        "summary": None,
        "error": None,
        "retry_count": 0
    }