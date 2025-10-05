"""Industry configurations for resume analysis."""

from typing import Dict, List
from pydantic import BaseModel, Field


class IndustryConfig(BaseModel):
    """Industry configuration model."""
    code: str = Field(..., description="Industry code")
    display_name: str = Field(..., description="Display name")
    key_skills: List[str] = Field(..., description="Key skills for this industry")


# Single source of truth for industry configurations
INDUSTRY_CONFIGS: Dict[str, Dict[str, any]] = {
    "tech_consulting": {
        "display_name": "Technology Consulting",
        "key_skills": [
            "Python",
            "JavaScript",
            "Cloud Architecture",
            "System Design",
            "Agile",
            "DevOps"
        ]
    },
    "finance_banking": {
        "display_name": "Finance & Banking",
        "key_skills": [
            "Financial Modeling",
            "Risk Management",
            "Regulatory Compliance",
            "Bloomberg",
            "Excel",
            "VBA"
        ]
    },
    "general_business": {
        "display_name": "General Business",
        "key_skills": [
            "Project Management",
            "Strategic Planning",
            "Data Analysis",
            "Leadership",
            "Communication",
            "Problem Solving"
        ]
    },
    "system_integrator": {
        "display_name": "Systems Integration",
        "key_skills": [
            "Systems Integration",
            "Enterprise Architecture",
            "API Development",
            "Database Management",
            "Testing",
            "Implementation"
        ]
    },
    "strategy_consulting": {
        "display_name": "Strategy Consulting",
        "key_skills": [
            "Strategic Analysis",
            "Market Research",
            "Business Modeling",
            "PowerPoint",
            "Excel",
            "Client Management"
        ]
    },
    "full_service_consulting": {
        "display_name": "Full Service Consulting",
        "key_skills": [
            "Business Analysis",
            "Change Management",
            "Process Improvement",
            "Stakeholder Management",
            "Presentation",
            "Analytics"
        ]
    }
}


def get_industry_config(industry_code: str) -> Dict[str, any]:
    """Get configuration for a specific industry.

    Args:
        industry_code: Industry code to look up

    Returns:
        Industry configuration dictionary

    Raises:
        KeyError: If industry code is not found
    """
    return INDUSTRY_CONFIGS.get(industry_code, INDUSTRY_CONFIGS["general_business"])


def get_supported_industries() -> List[IndustryConfig]:
    """Get list of all supported industries.

    Returns:
        List of IndustryConfig objects
    """
    return [
        IndustryConfig(
            code=code,
            display_name=config["display_name"],
            key_skills=config["key_skills"]
        )
        for code, config in INDUSTRY_CONFIGS.items()
    ]