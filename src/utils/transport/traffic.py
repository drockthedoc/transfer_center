"""
Traffic factor utilities for transport time estimation.

This module provides functions for estimating traffic factors based on time of day.
"""

import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Traffic patterns by time of day (multiplier on travel time)
# Index 0 = midnight, index 23 = 11 PM
TRAFFIC_PATTERNS = {
    # Houston traffic patterns (24-hour based)
    "houston": [
        0.8,  # 12 AM
        0.7,  # 1 AM
        0.6,  # 2 AM
        0.6,  # 3 AM
        0.7,  # 4 AM
        0.9,  # 5 AM
        1.4,  # 6 AM
        1.8,  # 7 AM
        1.7,  # 8 AM
        1.4,  # 9 AM
        1.2,  # 10 AM
        1.3,  # 11 AM
        1.4,  # 12 PM
        1.3,  # 1 PM
        1.2,  # 2 PM
        1.3,  # 3 PM
        1.5,  # 4 PM
        1.8,  # 5 PM
        1.7,  # 6 PM
        1.4,  # 7 PM
        1.2,  # 8 PM
        1.0,  # 9 PM
        0.9,  # 10 PM
        0.8,  # 11 PM
    ],
    # Austin traffic patterns
    "austin": [
        0.7,  # 12 AM
        0.6,  # 1 AM
        0.6,  # 2 AM
        0.6,  # 3 AM
        0.7,  # 4 AM
        1.0,  # 5 AM
        1.5,  # 6 AM
        1.9,  # 7 AM
        1.8,  # 8 AM
        1.3,  # 9 AM
        1.1,  # 10 AM
        1.2,  # 11 AM
        1.3,  # 12 PM
        1.2,  # 1 PM
        1.1,  # 2 PM
        1.2,  # 3 PM
        1.4,  # 4 PM
        1.9,  # 5 PM
        1.8,  # 6 PM
        1.4,  # 7 PM
        1.2,  # 8 PM
        1.0,  # 9 PM
        0.9,  # 10 PM
        0.8,  # 11 PM
    ],
}


def get_traffic_factor(metro_area: str, eta_minutes: Optional[int] = None) -> float:
    """
    Get the current traffic factor based on time of day and metro area.

    Args:
        metro_area: "houston" or "austin"
        eta_minutes: Minutes until ETA (if specified)

    Returns:
        Traffic factor multiplier
    """
    # Use the metro area patterns or default to houston
    patterns = TRAFFIC_PATTERNS.get(metro_area.lower(), TRAFFIC_PATTERNS["houston"])

    # Get current hour
    current_hour = datetime.now().hour

    # If eta_minutes is provided, adjust the hour accordingly
    if eta_minutes is not None:
        # Convert minutes to hours and add to current hour
        hour_offset = eta_minutes // 60  # Integer division
        future_hour = (current_hour + hour_offset) % 24  # Wrap around to 0-23
        traffic_factor = patterns[future_hour]
        logger.debug(
            f"Using future hour {future_hour} with traffic factor {traffic_factor}"
        )
    else:
        # Use current hour
        traffic_factor = patterns[current_hour]
        logger.debug(
            f"Using current hour {current_hour} with traffic factor {traffic_factor}"
        )

    return traffic_factor


def get_weather_adjustment(
    weather_condition: str, visibility_km: float, wind_speed_kph: float
) -> Dict[str, float]:
    """
    Calculate adjustments to travel time based on weather conditions.

    Args:
        weather_condition: Description of weather (e.g., "clear", "rain", "snow")
        visibility_km: Visibility in kilometers
        wind_speed_kph: Wind speed in kilometers per hour

    Returns:
        Dictionary of adjustment factors by transport mode
    """
    # Initialize with default (no adjustment) factors
    adjustments = {"ground": 1.0, "helicopter": 1.0, "fixed_wing": 1.0}

    # Adjust for weather condition
    weather_condition = weather_condition.lower()
    if "rain" in weather_condition:
        adjustments["ground"] *= 1.3  # 30% slower in rain

        if "heavy" in weather_condition:
            adjustments["ground"] *= 1.2  # Additional 20% slower in heavy rain
            adjustments["helicopter"] *= 1.5  # 50% slower or potentially unavailable

    elif "snow" in weather_condition:
        adjustments["ground"] *= 1.5  # 50% slower in snow
        adjustments["helicopter"] *= 1.3  # 30% slower in snow

        if "heavy" in weather_condition:
            adjustments["ground"] *= 1.5  # Additional 50% slower in heavy snow
            adjustments["helicopter"] *= 1.5  # Additional 50% slower in heavy snow

    elif "fog" in weather_condition or "mist" in weather_condition:
        if visibility_km < 5:
            adjustments["ground"] *= 1.2  # 20% slower in fog with reduced visibility

        if visibility_km < 2:
            adjustments["ground"] *= 1.3  # Additional 30% slower in dense fog
            adjustments["helicopter"] *= 2.0  # 100% slower or potentially unavailable

    # Adjust for wind
    if wind_speed_kph > 30:
        # Wind affects air transport more than ground
        wind_factor = min(2.0, 1.0 + (wind_speed_kph - 30) / 50)  # Cap at 2.0
        adjustments["helicopter"] *= wind_factor
        adjustments["fixed_wing"] *= (
            1.0 + (wind_factor - 1.0) / 2
        )  # Less impact on fixed wing

    # Adjust for visibility
    if visibility_km < 10:
        # Low visibility affects air transport
        visibility_factor = max(1.0, 2.0 - visibility_km / 10)  # Between 1.0 and 2.0
        adjustments["helicopter"] *= visibility_factor
        adjustments["fixed_wing"] *= (
            1.0 + (visibility_factor - 1.0) / 2
        )  # Less impact on fixed wing

    return adjustments
