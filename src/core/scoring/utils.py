#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Pediatric Scoring Utilities

Utility functions and common code patterns used by pediatric severity scoring systems.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Age-based reference ranges for vital signs
# Format: (min_age_months, max_age_months): (hr_min, hr_max, rr_min, rr_max)
AGE_BASED_RANGES = {
    (0, 3): (100, 150, 40, 60),  # 0-3 months
    (3, 12): (90, 120, 30, 45),  # 3-12 months
    (12, 36): (80, 115, 25, 40),  # 1-3 years
    (36, 72): (70, 110, 20, 30),  # 3-6 years
    (72, 144): (65, 100, 18, 25),  # 6-12 years
    (144, 216): (60, 90, 15, 20),  # 12-18 years
}

# Common mapping dictionaries
RESPIRATORY_EFFORT_MAP = {
    "normal": 0,
    "none": 0,
    "mild": 1,
    "slight": 1,
    "minimal": 1,
    "moderate": 2,
    "increased": 2,
    "labored": 2,
    "severe": 3,
    "significant": 3,
    "accessory muscles": 3,
    "grunting": 3,
}

OXYGEN_THERAPY_MAP = {
    "none": 0,
    "room air": 0,
    "ra": 0,
    "low flow": 1,
    "nasal cannula": 1,
    "simple mask": 1,
    "<30%": 1,
    "<2l": 1,
    "high flow": 2,
    "non-rebreather": 2,
    "cpap": 2,
    "bipap": 2,
    "30-40%": 2,
    "2-5l": 2,
    "ventilator": 3,
    "intubated": 3,
    "mechanical ventilation": 3,
    ">40%": 3,
    ">5l": 3,
}

MENTAL_STATUS_MAP = {
    "alert": 0,
    "a": 0,
    "normal": 0,
    "voice": 1,
    "v": 1,
    "responds to voice": 1,
    "pain": 2,
    "p": 2,
    "responds to pain": 2,
    "unresponsive": 3,
    "u": 3,
    "unconscious": 3,
}

BEHAVIOR_MAP = {
    "playing": 0,
    "appropriate": 0,
    "normal": 0,
    "sleeping": 0,
    "irritable": 1,
    "consolable": 1,
    "reduced": 2,
    "lethargic": 2,
    "confused": 2,
    "unresponsive": 3,
    "unconscious": 3,
}

HEMODYNAMIC_MAP = {
    "stable": 0,
    "normal": 0,
    "compensated": 1,
    "borderline": 1,
    "unstable": 2,
    "shock": 2,
    "decompensated": 2,
}


def get_age_based_ranges(age_months):
    """Get age-appropriate vital sign ranges

    Args:
        age_months: Age in months

    Returns:
        Dictionary with heart_rate and respiratory_rate ranges
    """
    if age_months is None:
        age_months = 60  # Default to 5 years if not specified

    for (min_age, max_age), (
        hr_min,
        hr_max,
        rr_min,
        rr_max,
    ) in AGE_BASED_RANGES.items():
        if min_age <= age_months < max_age:
            return {
                "heart_rate": (hr_min, hr_max),
                "respiratory_rate": (rr_min, rr_max),
            }

    # Default to adolescent values if age is outside ranges
    return {"heart_rate": (60, 90), "respiratory_rate": (15, 20)}


def safe_get_from_map(value, mapping, default=0):
    """Safely get a value from a mapping dictionary, handling None values

    Args:
        value: The key to look up
        mapping: Dictionary mapping
        default: Default value if key not found

    Returns:
        Mapped value or default
    """
    if value is None:
        return default
    return mapping.get(str(value).lower(), default)


def check_missing_params(required_params, critical_params=None):
    """Check for missing parameters and return appropriate data

    Args:
        required_params: Dictionary of parameter names to values
        critical_params: Dictionary of critical parameter names to values (subset of required)

    Returns:
        Tuple of (missing_params, missing_critical, has_missing_critical)
    """
    missing_params = [
        param for param, value in required_params.items() if value is None
    ]

    if critical_params:
        missing_critical = [
            param for param, value in critical_params.items() if value is None
        ]
        has_missing_critical = len(missing_critical) > 0
    else:
        missing_critical = missing_params
        has_missing_critical = len(missing_params) > 0

    return missing_params, missing_critical, has_missing_critical


def create_na_response(
    score_name,
    missing_params,
    subscore_keys,
    include_interpretation=True,
    include_action=True,
):
    """Create a standardized 'N/A' response for missing data

    Args:
        score_name: Name of the scoring system
        missing_params: List of missing parameter names
        subscore_keys: List of subscore keys to include
        include_interpretation: Whether to include interpretation field
        include_action: Whether to include action field

    Returns:
        Dictionary with standardized N/A response
    """
    response = {
        "score": "N/A",
        "missing_parameters": missing_params,
    }

    if include_interpretation:
        response["interpretation"] = (
            f"Cannot calculate {score_name}: missing required parameters"
        )

    if include_action:
        response["action"] = "N/A"

    response["subscores"] = {key: "N/A" for key in subscore_keys}

    return response


def normalize_to_risk_level(score, thresholds):
    """Convert a numeric score to a risk level based on thresholds

    Args:
        score: Numeric score
        thresholds: List of (threshold, level, action) tuples in ascending order

    Returns:
        Tuple of (risk_level, action)
    """
    for threshold, level, action in thresholds:
        if score <= threshold:
            return level, action

    # If no threshold matched, use the highest one
    return thresholds[-1][1], thresholds[-1][2]


def parse_numeric_or_map(value, mapping, default=0, max_value=3):
    """Parse a value that could be either numeric or a string to be mapped

    Args:
        value: The value to parse (could be numeric or string)
        mapping: Dictionary for string mapping
        default: Default value if parsing fails or value is None
        max_value: Maximum allowed value for numeric inputs

    Returns:
        Parsed numeric value
    """
    if value is None:
        return default

    # Try to handle it as a numeric value first
    if isinstance(value, (int, float)):
        return min(max_value, max(0, int(value)))

    # Handle as string
    try:
        # See if it can be converted to a number
        numeric_value = float(value)
        return min(max_value, max(0, int(numeric_value)))
    except (ValueError, TypeError):
        # Use the mapping
        return mapping.get(str(value).lower(), default)
