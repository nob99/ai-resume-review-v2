"""Summary generation service for resume analysis."""

from typing import Dict, Any, List


class SummaryGenerator:
    """Handles executive summary generation for resume analysis."""

    def __init__(self, thresholds: Dict[str, int], categories: Dict[str, str]):
        """Initialize the summary generator.

        Args:
            thresholds: Score thresholds (e.g., {"excellent": 80, "strong": 70, ...})
            categories: Category labels (e.g., {"excellent": "excellent candidate", ...})
        """
        self.thresholds = thresholds
        self.categories = categories

    def generate_summary(
        self,
        overall_score: float,
        market_tier: str,
        industry_name: str,
        structure_feedback: Dict[str, List[str]],
        appeal_feedback: Dict[str, List[str]]
    ) -> str:
        """Generate executive summary based on analysis results.

        Args:
            overall_score: Overall score (0-100)
            market_tier: Market tier (entry/mid/senior/executive)
            industry_name: Display name of the industry
            structure_feedback: Structure analysis feedback
            appeal_feedback: Appeal analysis feedback

        Returns:
            Executive summary text
        """
        # Determine category using thresholds
        category = self._determine_category(overall_score)

        # Get top strengths and improvements
        strengths = self._get_top_items(
            structure_feedback.get("strengths", []),
            appeal_feedback.get("competitive_advantages", []),
            max_items=2
        )
        improvements = appeal_feedback.get("improvement_areas", [])[:2]

        # Build summary
        summary_parts = [
            f"This resume scores {overall_score}/100, indicating a {category} candidate for {industry_name} roles.",
            f"The candidate appears to be at the {market_tier} level."
        ]

        if strengths:
            summary_parts.append(f"Key strengths include: {', '.join(strengths)}.")

        if improvements:
            summary_parts.append(f"Priority improvements: {', '.join(improvements)}.")

        return " ".join(summary_parts)

    def _determine_category(self, score: float) -> str:
        """Determine candidate category based on score.

        Args:
            score: Overall score

        Returns:
            Category label
        """
        if score >= self.thresholds.get("excellent", 80):
            return self.categories.get("excellent", "excellent candidate")
        elif score >= self.thresholds.get("strong", 70):
            return self.categories.get("strong", "strong candidate")
        elif score >= self.thresholds.get("good", 60):
            return self.categories.get("good", "good candidate")
        elif score >= self.thresholds.get("fair", 50):
            return self.categories.get("fair", "fair candidate")
        else:
            return self.categories.get("needs_improvement", "needs improvement")

    def _get_top_items(
        self,
        list1: List[str],
        list2: List[str],
        max_items: int = 2
    ) -> List[str]:
        """Combine and limit items from two lists.

        Args:
            list1: First list of items
            list2: Second list of items
            max_items: Maximum total items to return

        Returns:
            Combined list limited to max_items
        """
        # Take first item from each list
        combined = []
        if list1:
            combined.append(list1[0])
        if list2 and len(combined) < max_items:
            combined.append(list2[0])
        return combined
