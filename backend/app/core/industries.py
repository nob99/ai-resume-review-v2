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
    "ma_finance": {
        "display_name": "M&A & Financial Advisory",
        "key_skills": [
            "Financial Modeling",
            "M&A Analysis",
            "Due Diligence",
            "Valuation",
            "Deal Execution",
            "Excel"
        ]
    },
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
    if industry_code not in INDUSTRY_CONFIGS:
        raise KeyError(f"Industry code '{industry_code}' not found")
    return INDUSTRY_CONFIGS[industry_code]


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