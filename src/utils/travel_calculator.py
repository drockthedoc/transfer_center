"""
Calculates travel distance and time for road and air transport.

This module provides functions to estimate travel logistics:
- `get_road_travel_info`: Uses OSRM API for road travel and falls back to Haversine.
- `get_air_travel_info`: Calculates air travel viability and time based on weather
  and Haversine distance.
"""

import math  # math is not strictly needed here if only using Haversine from geolocation
from typing import Dict

import requests

from src.core.models import Location, WeatherData  # Add WeatherData
from src.utils.geolocation import calculate_distance  # For fallback and air travel

# OSRM API endpoint for driving directions
OSRM_API_URL = "http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
DEFAULT_AVERAGE_SPEED_KMH = 60  # For fallback calculation


def get_road_travel_info(origin: Location, destination: Location) -> Dict[str, any]:
    """
    Calculates road travel distance (km) and time (minutes) between two locations.
    Uses OSRM API if available, otherwise falls back to Haversine distance and average speed.

    Args:
        origin: The starting Location object (latitude, longitude).
        destination: The destination Location object (latitude, longitude).

    Returns:
        A dictionary containing:
            - "distance_km": Estimated road distance in kilometers.
            - "time_minutes": Estimated road travel time in minutes.
            - "source": A string indicating the source of the data ("OSRM API" or
                        "Fallback Haversine/Average Speed").
    """
    url = OSRM_API_URL.format(
        lon1=origin.longitude,
        lat1=origin.latitude,
        lon2=destination.longitude,
        lat2=destination.latitude,
    )

    try:
        # print(f"Attempting OSRM API call: {url}") # Optional: for worker debugging
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        data = response.json()

        if (
            data.get("routes") and data["routes"][0]
        ):  # Check if 'routes' is not empty and has at least one route
            route = data["routes"][0]
            distance_m = route.get("distance")  # Meters
            duration_s = route.get("duration")  # Seconds

            if distance_m is not None and duration_s is not None:
                # print(f"OSRM API success for {origin} to {destination}") # Optional:
                # for worker debugging
                return {
                    "distance_km": round(distance_m / 1000, 2),
                    "time_minutes": round(duration_s / 60, 2),
                    "source": "OSRM API",
                }
            else:
                # API returned a route but it was missing distance or duration
                print(
                    f"Warning: OSRM API route for {origin} to {destination} is incomplete. Using fallback."
                )
        else:
            # API returned success but no route found (e.g. 'routes' was empty or not
            # present)
            print(
                f"Warning: OSRM API found no route between {origin} and {destination}. Using fallback."
            )

    except requests.exceptions.Timeout:
        print(
            f"Warning: OSRM API request timed out for route {origin} to {destination}. Using fallback."
        )
    except requests.exceptions.HTTPError as e:
        # Specific handling for HTTP errors (e.g. 400, 404, 500)
        print(f"Warning: OSRM API request failed with HTTPError {e.response.status_code} for route {origin} to {destination}. Using fallback.")
    except requests.exceptions.ConnectionError:
        print(
            f"Warning: OSRM API request failed due to connection error for route {origin} to {destination}. Using fallback."
        )
    except (
        requests.exceptions.RequestException
    ) as e:  # Catch-all for other requests issues
        print(
            f"Warning: OSRM API request failed for route {origin} to {destination}: {e}. Using fallback."
        )
    except (
        KeyError,
        IndexError,
        ValueError,
    ) as e:  # For issues with JSON parsing (e.g. data['routes'][0] fails)
        print(
            f"Warning: Error parsing OSRM API response for route {origin} to {destination}: {e}. Using fallback."
        )

    # Fallback mechanism
    # print(f"Executing fallback for {origin} to {destination}") # Optional:
    # for worker debugging
    haversine_dist_km = calculate_distance(origin, destination)
    # Ensure time is not zero if distance is very small but non-zero
    # Ensure DEFAULT_AVERAGE_SPEED_KMH is not zero to prevent DivisionByZeroError
    estimated_time_min = (
        (haversine_dist_km / DEFAULT_AVERAGE_SPEED_KMH) * 60
        if DEFAULT_AVERAGE_SPEED_KMH > 0
        else 0
    )

    return {
        "distance_km": round(haversine_dist_km, 2),
        "time_minutes": round(estimated_time_min, 2),
        "source": "Fallback Haversine/Average Speed",
    }


# Constants for air travel
ADVERSE_WEATHER_FOR_AIR_TRAVEL = [
    "FOG",
    "THUNDERSTORM",
    "HIGH_WINDS",
    "BLIZZARD",
    "FREEZING_RAIN",
    "HURRICANE",
    "SEVERE TURBULENCE",
]
MIN_VISIBILITY_KM_VFR = 1.5
MAX_WIND_SPEED_KPH_AIR = 70.0


def get_air_travel_info(
    origin: Location,
    destination_helipad_location: Location,
    weather: WeatherData,
    average_helicopter_speed_kmh: float = 240.0,
    fixed_maneuver_time_minutes: float = 20.0,
) -> Dict[str, any]:
    """
    Calculates air travel viability, distance (km), and time (minutes)
    between an origin and a destination helipad location, considering weather.

    Args:
        origin: The starting Location object.
        destination_helipad_location: The Location object of the destination helipad.
        weather: A WeatherData object with current weather conditions.
        average_helicopter_speed_kmh: Average speed of the helicopter in km/h.
        fixed_maneuver_time_minutes: Fixed time in minutes for takeoff, landing,
                                     and other maneuvers.

    Returns:
        A dictionary containing:
            - "viable": Boolean indicating if air travel is viable.
            - "reason": String explaining non-viability or confirming suitability.
            - "distance_km": Air (Haversine) distance in kilometers.
            - "time_minutes": Estimated total air travel time in minutes if viable,
                              otherwise 0 or float('inf').
            - "source": String indicating "Air Travel Calculation".
    """
    if weather.adverse_conditions:
        for condition in weather.adverse_conditions:
            # Case-insensitive check for adverse conditions
            if condition.upper() in [
                adv_cond.upper() for adv_cond in ADVERSE_WEATHER_FOR_AIR_TRAVEL
            ]:
                return {
                    "viable": False,
                    "reason": f"Adverse weather: {condition}.",
                    "distance_km": 0,
                    "time_minutes": 0,
                    "source": "Air Travel Calculation",
                }

    if weather.visibility_km < MIN_VISIBILITY_KM_VFR:
        return {
            "viable": False,
            "reason": f"Visibility {weather.visibility_km}km < minimum {MIN_VISIBILITY_KM_VFR}km for VFR.",
            "distance_km": 0,
            "time_minutes": 0,
            "source": "Air Travel Calculation",
        }

    if weather.wind_speed_kph > MAX_WIND_SPEED_KPH_AIR:
        return {
            "viable": False,
            "reason": f"Wind speed {weather.wind_speed_kph}kph > maximum {MAX_WIND_SPEED_KPH_AIR}kph.",
            "distance_km": 0,
            "time_minutes": 0,
            "source": "Air Travel Calculation",
        }

    # If weather is viable, calculate distance and time
    distance_km = calculate_distance(origin, destination_helipad_location)

    if average_helicopter_speed_kmh <= 0:
        return {
            "viable": False,
            "reason": "Average helicopter speed must be positive.",
            "distance_km": round(distance_km, 2),
            "time_minutes": float("inf"),
            "source": "Air Travel Calculation",
        }

    flight_duration_minutes = (distance_km / average_helicopter_speed_kmh) * 60
    total_time_minutes = flight_duration_minutes + fixed_maneuver_time_minutes

    return {
        "viable": True,
        "reason": "Weather conditions suitable for air travel.",
        "distance_km": round(distance_km, 2),
        "time_minutes": round(total_time_minutes, 2),
        "source": "Air Travel Calculation",
    }
