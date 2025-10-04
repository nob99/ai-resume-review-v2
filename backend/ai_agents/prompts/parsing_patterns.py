"""Shared regex patterns for parsing LLM responses.

This module defines common regex patterns used across all prompt YAML files
to eliminate duplication and ensure consistency.
"""

# Common pattern building blocks
COLON_SEP = "[：:\\s]*"  # Matches both English and Japanese colons with optional whitespace
DIGIT_GROUP = "(\\d+)"   # Captures one or more digits

# Score extraction patterns (used in both structure and appeal prompts)
SCORE_PATTERNS = {
    "generic_score": f"{{label}}{COLON_SEP}{DIGIT_GROUP}",
}

# Market tier pattern (used in appeal prompts)
MARKET_TIER_PATTERN = f"{{label}}{COLON_SEP}(entry|mid|senior|executive)"

# Metadata patterns (used in structure prompts)
METADATA_PATTERNS = {
    "count": f"{{label}}{COLON_SEP}{DIGIT_GROUP}",
    "time": f"{{label}}{COLON_SEP}{DIGIT_GROUP}",
}


def build_score_pattern(label: str) -> str:
    """Build a score extraction pattern for a given label.

    Args:
        label: The label text to match (e.g., "Format Score" or "フォーマットスコア")

    Returns:
        Complete regex pattern string

    Example:
        >>> build_score_pattern("Format Score")
        'Format Score[：:\\s]*(\\d+)'
    """
    return SCORE_PATTERNS["generic_score"].format(label=label)


def build_market_tier_pattern(label: str) -> str:
    """Build a market tier extraction pattern for a given label.

    Args:
        label: The label text to match (e.g., "Market Tier" or "市場ティア")

    Returns:
        Complete regex pattern string
    """
    return MARKET_TIER_PATTERN.format(label=label)


def build_metadata_pattern(label: str, pattern_type: str = "count") -> str:
    """Build a metadata extraction pattern for a given label.

    Args:
        label: The label text to match
        pattern_type: Type of pattern ("count" or "time")

    Returns:
        Complete regex pattern string
    """
    return METADATA_PATTERNS[pattern_type].format(label=label)
