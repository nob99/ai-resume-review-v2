"""Context building utilities for AI agents."""

from typing import Dict, Any


def build_structure_context(state: Dict[str, Any]) -> str:
    """Build context string from structure analysis results.

    Args:
        state: Current state with structure analysis results

    Returns:
        Formatted context string for use in prompts
    """
    if not state.get("structure_scores"):
        return ""

    scores = state["structure_scores"]
    feedback = state.get("structure_feedback", {})

    context_parts = [
        "STRUCTURE ANALYSIS CONTEXT:",
        f"- Format Score: {scores.get('format', 0)}/100",
        f"- Organization Score: {scores.get('organization', 0)}/100",
        f"- Professional Tone Score: {scores.get('tone', 0)}/100",
        f"- Completeness Score: {scores.get('completeness', 0)}/100"
    ]

    if feedback.get("issues"):
        issues = feedback["issues"][:3]  # Top 3 issues
        context_parts.append(f"- Key Issues: {', '.join(issues)}")

    if feedback.get("strengths"):
        strengths = feedback["strengths"][:2]  # Top 2 strengths
        context_parts.append(f"- Strengths: {', '.join(strengths)}")

    return "\n".join(context_parts)
