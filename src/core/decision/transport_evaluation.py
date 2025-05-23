"""
Transport evaluation component for the Transfer Center decision engine.

This module handles evaluating transport options and times between locations.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

from src.core.models import (
    HospitalCampus,
    Location,
    TransportMode,
    WeatherData
)

logger = logging.getLogger(__name__)


def evaluate_transport_options(
    sending_location: Location,
    campus: HospitalCampus,
    available_transport_modes: List[TransportMode],
    weather_data: WeatherData,
    transport_time_estimates: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[Optional[str], Optional[float]]:
    """
    Evaluate transport options between sending location and hospital campus.
    
    Args:
        sending_location: Location of sending facility
        campus: Target hospital campus
        available_transport_modes: List of available transport modes
        weather_data: Current weather data
        transport_time_estimates: Optional pre-calculated transport time estimates
        
    Returns:
        Tuple of (best_transport_mode, travel_time_minutes)
        Returns (None, None) if no viable transport option is found
    """
    logger.info(f"Evaluating transport options to {campus.name}")
    
    # Check if we have pre-calculated time estimates
    if transport_time_estimates and campus.campus_id in transport_time_estimates:
        campus_estimate = transport_time_estimates[campus.campus_id]
        
        if "time_minutes" in campus_estimate and "mode" in campus_estimate:
            return campus_estimate["mode"], campus_estimate["time_minutes"]
    
    # If no pre-calculated estimates, use simple distance-based calculation
    # For simplicity, we'll use TransportMode.GROUND_AMBULANCE as default
    best_mode = "Ground Ambulance"
    
    # Calculate a simple distance-based travel time
    from math import radians, cos, sin, asin, sqrt
    
    def haversine_distance(loc1: Location, loc2: Location) -> float:
        """Calculate the distance between two locations in kilometers."""
        # Convert latitude and longitude from degrees to radians
        lon1, lat1 = radians(loc1.longitude), radians(loc1.latitude)
        lon2, lat2 = radians(loc2.longitude), radians(loc2.latitude)
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of earth in kilometers
        
        return c * r
    
    # Calculate distance
    distance_km = haversine_distance(sending_location, campus.location)
    
    # Estimate travel time based on mode and distance
    # These are simplified estimates and should be replaced with actual calculations
    travel_times = {}
    
    if TransportMode.GROUND_AMBULANCE in available_transport_modes:
        # Assume average speed of 80 km/h for ground ambulance
        travel_times["Ground Ambulance"] = distance_km / 80 * 60  # minutes
    
    if TransportMode.HELICOPTER in available_transport_modes:
        # Assume average speed of 240 km/h for helicopter
        # Only viable if distance is between 20km and 250km
        if 20 <= distance_km <= 250:
            travel_times["Helicopter"] = distance_km / 240 * 60  # minutes
        
    if TransportMode.FIXED_WING in available_transport_modes:
        # Assume average speed of 450 km/h for fixed-wing aircraft
        # Only viable if distance is over 100km
        if distance_km > 100:
            travel_times["Fixed Wing"] = distance_km / 450 * 60  # minutes
    
    # Weather adjustments
    # Adjust travel times based on weather conditions
    weather_condition = weather_data.weather_condition.lower()
    visibility_km = weather_data.visibility_km
    wind_speed_kph = weather_data.wind_speed_kph
    
    # Apply weather adjustments
    if "rain" in weather_condition or "snow" in weather_condition or "fog" in weather_condition:
        if "Ground Ambulance" in travel_times:
            travel_times["Ground Ambulance"] *= 1.3  # 30% slower in bad weather
        
        if visibility_km < 5:  # Poor visibility
            if "Helicopter" in travel_times:
                if visibility_km < 2:
                    # Too dangerous for helicopter in very poor visibility
                    travel_times.pop("Helicopter")
                else:
                    travel_times["Helicopter"] *= 1.5  # 50% slower in poor visibility
    
    if wind_speed_kph > 50:  # High winds
        if "Helicopter" in travel_times:
            if wind_speed_kph > 80:
                # Too dangerous for helicopter in very high winds
                travel_times.pop("Helicopter")
            else:
                travel_times["Helicopter"] *= 1.3  # 30% slower in high winds
        
        if "Fixed Wing" in travel_times:
            travel_times["Fixed Wing"] *= 1.2  # 20% slower in high winds
    
    # Select best mode (shortest travel time)
    if travel_times:
        best_mode = min(travel_times.items(), key=lambda x: x[1])[0]
        best_time = travel_times[best_mode]
        
        logger.info(f"Best transport mode to {campus.name}: {best_mode}, {best_time:.1f} minutes")
        return best_mode, best_time
    else:
        logger.warning(f"No viable transport options found for {campus.name}")
        return None, None


def calculate_total_transport_time(
    transport_mode: str,
    travel_time_minutes: float,
    preparation_time_minutes: float = 15.0
) -> float:
    """
    Calculate the total transport time including preparation.
    
    Args:
        transport_mode: Transport mode being used
        travel_time_minutes: Direct travel time in minutes
        preparation_time_minutes: Time needed for preparation (default: 15 minutes)
        
    Returns:
        Total transport time in minutes
    """
    # Add mode-specific preparation times
    if "Helicopter" in transport_mode:
        # Helicopter typically needs more preparation time
        preparation_time_minutes += 15.0
    elif "Fixed Wing" in transport_mode:
        # Fixed wing aircraft needs even more preparation
        preparation_time_minutes += 30.0
    
    # Calculate total time
    total_time = travel_time_minutes + preparation_time_minutes
    
    logger.info(f"Total transport time ({transport_mode}): {total_time:.1f} minutes "
               f"(travel: {travel_time_minutes:.1f}, prep: {preparation_time_minutes:.1f})")
    
    return total_time
