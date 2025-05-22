import math
from src.core.models import Location

def calculate_distance(coord1: Location, coord2: Location) -> float:
    """
    Calculate the distance between two geographical coordinates using the Haversine formula.

    Args:
        coord1: The first Location object (latitude, longitude in degrees).
        coord2: The second Location object (latitude, longitude in degrees).

    Returns:
        The distance between the two coordinates in kilometers.
    """
    # Earth radius in kilometers
    R = 6371.0

    lat1_rad = math.radians(coord1.latitude)
    lon1_rad = math.radians(coord1.longitude)
    lat2_rad = math.radians(coord2.latitude)
    lon2_rad = math.radians(coord2.longitude)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance_km = R * c
    return distance_km
