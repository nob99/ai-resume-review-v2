"""Scoring calculation service for resume analysis."""

from typing import Dict, Any


class ScoreCalculator:
    """Handles weighted score calculations for resume analysis."""

    def __init__(self, scoring_weights: Dict[str, float]):
        """Initialize the score calculator.

        Args:
            scoring_weights: Dictionary of agent weights (e.g., {"structure": 0.4, "appeal": 0.6})
        """
        self.weights = scoring_weights

    def calculate_overall_score(self, state: Dict[str, Any]) -> float:
        """Calculate weighted overall score from structure and appeal scores.

        Args:
            state: State dictionary containing structure_scores and appeal_scores

        Returns:
            Overall score (0-100)
        """
        structure_weight = self.weights.get("structure", 0.4)
        appeal_weight = self.weights.get("appeal", 0.6)

        # Calculate structure average
        structure_scores = state.get("structure_scores", {})
        structure_avg = self._calculate_average(structure_scores)

        # Calculate appeal average
        appeal_scores = state.get("appeal_scores", {})
        appeal_avg = self._calculate_average(appeal_scores)

        # Calculate weighted overall score
        overall = (structure_avg * structure_weight) + (appeal_avg * appeal_weight)

        return round(overall, 1)

    def _calculate_average(self, scores: Dict[str, float]) -> float:
        """Calculate average of score values.

        Args:
            scores: Dictionary of scores

        Returns:
            Average score or 0 if empty
        """
        if not scores:
            return 0.0
        return sum(scores.values()) / len(scores)
