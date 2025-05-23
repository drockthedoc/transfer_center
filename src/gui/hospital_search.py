"""
Hospital search functionality for the Transfer Center GUI.

This module provides geolocation and hospital search capabilities.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim

# Set up logging
logger = logging.getLogger(__name__)


class HospitalSearch:
    """
    Provides hospital search and geolocation functionality.
    """

    def __init__(self):
        """Initialize the hospital search module."""
        self.geolocator = Nominatim(user_agent="transfer_center_app")
        self.hospitals_cache = {}
        self.load_hospitals()

    def load_hospitals(self) -> None:
        """Load hospital data from sample file and any additional sources."""
        try:
            # Load from sample hospital data
            hospital_path = Path("data/sample_hospital_campuses.json")
            if hospital_path.exists():
                with open(hospital_path, "r") as f:
                    hospitals_data = json.load(f)
                    for hospital in hospitals_data:
                        name = hospital.get("name", "Unknown")
                        self.hospitals_cache[name] = {
                            "latitude": hospital.get("location", {}).get("latitude", 0),
                            "longitude": hospital.get("location", {}).get(
                                "longitude", 0
                            ),
                            "address": hospital.get("address", ""),
                            "campus_id": hospital.get("campus_id", ""),
                        }

            # Load additional common hospitals in Texas for the demo
            texas_hospitals = [
                {
                    "name": "Memorial Hermann Houston",
                    "address": "6411 Fannin St, Houston, TX 77030",
                },
                {
                    "name": "Houston Methodist Hospital",
                    "address": "6565 Fannin St, Houston, TX 77030",
                },
                {
                    "name": "Dell Children's Medical Center",
                    "address": "4900 Mueller Blvd, Austin, TX 78723",
                },
                {
                    "name": "St. David's Medical Center Austin",
                    "address": "919 E 32nd St, Austin, TX 78705",
                },
                {
                    "name": "Children's Health Dallas",
                    "address": "1935 Medical District Dr, Dallas, TX 75235",
                },
                {
                    "name": "CHRISTUS Trinity Mother Frances",
                    "address": "800 E Dawson St, Tyler, TX 75701",
                },
                {
                    "name": "University Hospital San Antonio",
                    "address": "4502 Medical Dr, San Antonio, TX 78229",
                },
                {
                    "name": "Baylor Scott & White Temple",
                    "address": "2401 S 31st St, Temple, TX 76508",
                },
            ]

            # Geocode these hospitals if not already in cache
            for hospital in texas_hospitals:
                if hospital["name"] not in self.hospitals_cache:
                    # Try to geocode the address
                    try:
                        location = self.geolocator.geocode(
                            hospital["address"], timeout=5
                        )
                        if location:
                            self.hospitals_cache[hospital["name"]] = {
                                "latitude": location.latitude,
                                "longitude": location.longitude,
                                "address": hospital["address"],
                                "campus_id": "",  # External hospital, no campus ID
                            }
                    except (GeocoderTimedOut, GeocoderUnavailable) as e:
                        logger.warning(
                            f"Could not geocode {hospital['name']}: {str(e)}"
                        )

            logger.info(f"Loaded {len(self.hospitals_cache)} hospitals")

        except Exception as e:
            logger.error(f"Error loading hospitals: {str(e)}")

    def search_hospitals(self, query: str) -> List[Dict]:
        """
        Search for hospitals by name or address.

        Args:
            query: Hospital name or address to search for

        Returns:
            List of matching hospitals with their details
        """
        query = query.lower()
        results = []

        # Search in cache first
        for name, details in self.hospitals_cache.items():
            if query in name.lower() or (
                details.get("address", "") and query in details["address"].lower()
            ):
                results.append(
                    {
                        "name": name,
                        "latitude": details["latitude"],
                        "longitude": details["longitude"],
                        "address": details.get("address", ""),
                        "campus_id": details.get("campus_id", ""),
                    }
                )

        # If no results and query is long enough, try geocoding as an address
        if not results and len(query) > 5:
            try:
                location = self.geolocator.geocode(query, timeout=5)
                if location:
                    results.append(
                        {
                            "name": location.address,
                            "latitude": location.latitude,
                            "longitude": location.longitude,
                            "address": location.address,
                            "campus_id": "",
                        }
                    )
            except (GeocoderTimedOut, GeocoderUnavailable) as e:
                logger.warning(f"Geocoding failed: {str(e)}")

        return results

    def geocode_address(self, address: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Geocode an address to get coordinates.

        Args:
            address: The address to geocode

        Returns:
            Tuple of (latitude, longitude) or (None, None) if geocoding failed
        """
        try:
            location = self.geolocator.geocode(address, timeout=5)
            if location:
                return location.latitude, location.longitude
            return None, None
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            logger.warning(f"Geocoding failed: {str(e)}")
            return None, None
