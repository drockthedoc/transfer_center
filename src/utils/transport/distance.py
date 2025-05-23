"""
Distance calculation utilities for transport time estimation.

This module provides functions for calculating distances between locations.
"""

import math
from typing import Tuple

from src.core.models import Location


def calculate_distance(loc1: Location, loc2: Location) -> float:
    """
    Calculate the distance between two locations using the Haversine formula.

    Args:
        loc1: First location
        loc2: Second location

    Returns:
        Distance in kilometers
    """
    # Earth radius in kilometers
    R = 6371.0

    # Convert latitude and longitude from degrees to radians
    lat1 = math.radians(loc1.latitude)
    lon1 = math.radians(loc1.longitude)
    lat2 = math.radians(loc2.latitude)
    lon2 = math.radians(loc2.longitude)

    # Differences
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    # Haversine formula
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    return distance


def calculate_direct_travel_time(distance: float, speed_kph: float) -> float:
    """
    Calculate the direct travel time between two points.

    Args:
        distance: Distance in kilometers
        speed_kph: Speed in kilometers per hour

    Returns:
        Travel time in minutes
    """
    # Calculate travel time in hours then convert to minutes
    travel_time_hours = distance / speed_kph
    travel_time_minutes = travel_time_hours * 60

    return travel_time_minutes


def get_coordinates_by_metro_area(metro_area: str) -> Tuple[float, float]:
    """
    Get the approximate coordinates of a metro area center.

    Args:
        metro_area: Name of the metro area ("houston" or "austin")

    Returns:
        Tuple of (latitude, longitude)
    """
    if metro_area.lower() == "houston":
        return 29.7604, -95.3698  # Downtown Houston
    elif metro_area.lower() == "austin":
        return 30.2672, -97.7431  # Downtown Austin
    else:
        # Default to Houston if unknown
        return 29.7604, -95.3698
