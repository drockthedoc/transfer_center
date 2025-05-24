"""
Transport time estimator for the Transfer Center.

This module handles the estimation of transport times between locations based on
different transport modes, traffic patterns, and specialized transport services.
"""

import logging
import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.core.models import HospitalCampus, Location, TransportMode
from src.utils.transport.distance import (
    calculate_direct_travel_time,
    calculate_distance,
    get_coordinates_by_metro_area,
)
from src.utils.transport.traffic import get_traffic_factor, get_weather_adjustment

logger = logging.getLogger(__name__)


class TransportTimeEstimator:
    """
    Estimates transport times based on locations, modes, and conditions.

    This class calculates estimated transport times between sending facilities
    and receiving hospitals, accounting for different transport modes, traffic
    patterns, and specialized transport services like Kangaroo Crew.
    """

    def __init__(self):
        """Initialize the transport time estimator."""
        # Houston and Austin metro center coordinates (approximate)
        self.houston_center = Location(latitude=29.7604, longitude=-95.3698)
        self.austin_center = Location(latitude=30.2672, longitude=-97.7431)

        # Kangaroo Crew base locations
        self.kc_bases = {
            "houston": Location(
                latitude=29.7604, longitude=-95.3698
            ),  # Texas Children's Hospital
            "austin": Location(latitude=30.2672, longitude=-97.7431),  # Austin base
        }

        # Average speeds for different transport modes (km/h)
        self.speeds = {
            "ground": 80.0,  # Average ground ambulance speed
            "helicopter": 240.0,  # Average helicopter speed
            "fixed_wing": 450.0,  # Average fixed-wing aircraft speed
            "pov": 70.0,  # Average private vehicle speed
        }

    def _get_metro_area(self, location: Location) -> str:
        """
        Determine which metro area a location is in (or closest to).

        Args:
            location: The location to check

        Returns:
            "houston" or "austin" based on proximity
        """
        # Calculate distances to each metro area
        dist_to_houston = calculate_distance(location, self.houston_center)
        dist_to_austin = calculate_distance(location, self.austin_center)

        # Return the closest metro area
        return "houston" if dist_to_houston <= dist_to_austin else "austin"

    def _calculate_kangaroo_crew_time(
        self,
        sending_location: Location,
        receiving_location: Location,
        mode: str = "ground",
    ) -> Tuple[float, str]:
        """
        Calculate transport time using Kangaroo Crew, accounting for crew dispatch.

        Args:
            sending_location: Location of sending facility
            receiving_location: Location of receiving hospital
            mode: Transport mode ("ground" or "helicopter")

        Returns:
            Tuple of (time_in_minutes, notes)
        """
        # Determine which metro area the sending location is in/closest to
        metro_area = self._get_metro_area(sending_location)

        # Get the Kangaroo Crew base for that metro area
        kc_base = self.kc_bases[metro_area]

        # Calculate distances
        base_to_sender_distance = calculate_distance(kc_base, sending_location)
        sender_to_receiver_distance = calculate_distance(
            sending_location, receiving_location
        )

        # Get speed for the selected mode
        speed = self.speeds.get(mode, self.speeds["ground"])

        # Calculate travel times
        base_to_sender_time = calculate_direct_travel_time(
            base_to_sender_distance, speed
        )
        sender_to_receiver_time = calculate_direct_travel_time(
            sender_to_receiver_distance, speed
        )

        # Get traffic factors for both legs
        traffic_factor1 = get_traffic_factor(metro_area)

        # For the second leg, determine the metro area of the destination
        dest_metro_area = self._get_metro_area(receiving_location)

        # Estimate time until the second leg starts
        time_until_second_leg = (
            30 + base_to_sender_time
        )  # 30 min prep + travel to sender

        # Get traffic factor for the second leg
        traffic_factor2 = get_traffic_factor(
            dest_metro_area, int(time_until_second_leg)
        )

        # Apply traffic factors
        if mode == "ground":  # Air transport isn't affected by traffic
            base_to_sender_time *= traffic_factor1
            sender_to_receiver_time *= traffic_factor2

        # Additional times
        prep_time = 30.0  # 30 minutes to prepare the crew
        patient_prep_time = 20.0  # 20 minutes to prepare the patient

        # Calculate total time
        total_time = (
            prep_time
            + base_to_sender_time
            + patient_prep_time
            + sender_to_receiver_time
        )

        # Notes about the calculation
        notes = (
            f"KC {mode} transport: {total_time:.1f} min total "
            f"({prep_time:.1f} min prep + {base_to_sender_time:.1f} min to sender + "
            f"{patient_prep_time:.1f} min patient prep + {sender_to_receiver_time:.1f} min to receiver)"
        )

        if mode == "ground":
            notes += f", traffic_factor: {(traffic_factor1 + traffic_factor2) / 2:.2f}"

        return total_time, notes

    def estimate_transport_times(
        self,
        sending_location: Location,
        hospitals: List[HospitalCampus],
        transport_modes: List[TransportMode],
        minutes_until_eta: Optional[int] = None,
        transport_type: str = "Local EMS",
        kc_mode: str = "ground",
    ) -> Dict[str, Dict[str, Any]]:
        """
        Estimate transport times from sending location to all hospitals.

        Args:
            sending_location: Location of sending facility
            hospitals: List of potential receiving hospitals
            transport_modes: List of available transport modes
            minutes_until_eta: Optional minutes until estimated time of arrival
            transport_type: Type of transport service ("Local EMS" or "Kangaroo Crew")
            kc_mode: Kangaroo Crew transport mode ("ground" or "helicopter")

        Returns:
            Dictionary of estimated times by hospital ID:
            {
                "hospital_id": {
                    "time_minutes": float,
                    "distance_km": float,
                    "mode": str,
                    "traffic_factor": float,
                    "notes": str
                }
            }
        """
        logger.info(f"Estimating transport times for {len(hospitals)} hospitals")

        # Determine the metro area of the sending location for traffic estimates
        metro_area = self._get_metro_area(sending_location)
        logger.debug(f"Sending location is in/closest to {metro_area} metro area")

        # Get current traffic factor based on time of day
        traffic_factor = get_traffic_factor(metro_area, minutes_until_eta)
        logger.debug(f"Current traffic factor: {traffic_factor}")

        # Initialize results dictionary
        results = {}

        # Process each hospital
        for hospital in hospitals:
            # Calculate distance
            distance = calculate_distance(sending_location, hospital.location)
            logger.debug(f"Distance to {hospital.name}: {distance:.1f} km")

            # Initialize best time tracking
            best_time = float("inf")
            best_mode = None
            best_notes = ""

            # If using Kangaroo Crew, calculate specialized times
            if transport_type == "Kangaroo Crew":
                time_minutes, notes = self._calculate_kangaroo_crew_time(
                    sending_location, hospital.location, kc_mode
                )

                best_time = time_minutes
                best_mode = f"Kangaroo Crew ({kc_mode})"
                best_notes = notes

                logger.debug(
                    f"Kangaroo Crew time to {hospital.name}: {time_minutes:.1f} minutes"
                )

            # Otherwise, calculate times for each available transport mode
            else:
                for mode in transport_modes:
                    # Convert TransportMode enum to string
                    mode_str = str(mode).split(".")[-1]

                    # Map to speed key
                    speed_key = "ground"
                    if mode == TransportMode.HELICOPTER:
                        speed_key = "helicopter"
                    elif mode == TransportMode.FIXED_WING:
                        speed_key = "fixed_wing"

                    # Get speed for this mode
                    speed = self.speeds[speed_key]

                    # Calculate base travel time
                    time_minutes = calculate_direct_travel_time(distance, speed)

                    # Apply traffic factor for ground transport
                    notes = ""
                    if speed_key == "ground":
                        time_minutes *= traffic_factor
                        notes = f"traffic_factor: {traffic_factor:.2f}"
                    else:
                        notes = "Air medical transport"

                    # Check if this mode is better than current best
                    if time_minutes < best_time:
                        best_time = time_minutes
                        best_mode = mode_str
                        best_notes = notes

                    logger.debug(
                        f"{mode_str} time to {hospital.name}: {time_minutes:.1f} minutes"
                    )

            # Add random variation (±10%) to simulate real-world variability
            variation_factor = 1.0 + random.uniform(-0.1, 0.1)
            best_time *= variation_factor

            # Round time to nearest minute
            best_time = round(best_time)

            # Store results
            results[hospital.campus_id] = {
                "time_minutes": best_time,
                "distance_km": distance,
                "mode": best_mode,
                "traffic_factor": (
                    traffic_factor if "traffic_factor" in best_notes else 1.0
                ),
                "notes": best_notes,
            }

        return results


# Example usage when run directly
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Create estimator
    estimator = TransportTimeEstimator()

    # Example locations
    sending = Location(latitude=29.8, longitude=-95.5)  # Example sending facility

    # Example hospitals
    hospitals = [
        HospitalCampus(
            campus_id="TCH_MED_CTR",
            name="Texas Children's Hospital Medical Center",
            metro_area="HOUSTON_METRO",
            address="6621 Fannin St, Houston, TX 77030",
            location=Location(latitude=29.7070, longitude=-95.4017),
            bed_census={
                "total_beds": 500,
                "available_beds": 50,
                "icu_beds_total": 100,
                "icu_beds_available": 10,
                "nicu_beds_total": 80,
                "nicu_beds_available": 8,
            },
            exclusions=[],
            helipads=[],
        ),
        HospitalCampus(
            campus_id="TCH_WEST",
            name="Texas Children's Hospital West Campus",
            metro_area="HOUSTON_METRO",
            address="18200 Katy Freeway, Houston, TX 77094",
            location=Location(latitude=29.7850, longitude=-95.7012),
            bed_census={
                "total_beds": 300,
                "available_beds": 30,
                "icu_beds_total": 50,
                "icu_beds_available": 5,
                "nicu_beds_total": 40,
                "nicu_beds_available": 4,
            },
            exclusions=[],
            helipads=[],
        ),
    ]

    # Estimate transport times
    print("Example Transport Time Estimation:")

    # Local EMS
    print("\nLocal EMS:")
    local_ems_times = estimator.estimate_transport_times(
        sending, hospitals, [TransportMode.GROUND_AMBULANCE], transport_type="Local EMS"
    )
    for hospital_id, details in local_ems_times.items():
        print(
            f"{hospital_id}: {details['time_minutes']} minutes, "
            f"{details['distance_km']:.1f} km, {details['mode']}"
        )

    # Kangaroo Crew (ground)
    print("\nKangaroo Crew (ground):")
    kc_ground_times = estimator.estimate_transport_times(
        sending,
        hospitals,
        [],  # Not used for KC
        transport_type="Kangaroo Crew",
        kc_mode="ground",
    )
    for hospital_id, details in kc_ground_times.items():
        print(
            f"{hospital_id}: {details['time_minutes']} minutes, "
            f"{details['distance_km']:.1f} km, {details['mode']}"
        )

    # Kangaroo Crew (helicopter)
    print("\nKangaroo Crew (helicopter):")
    kc_heli_times = estimator.estimate_transport_times(
        sending,
        hospitals,
        [],  # Not used for KC
        transport_type="Kangaroo Crew",
        kc_mode="helicopter",
    )
    for hospital_id, details in kc_heli_times.items():
        print(
            f"{hospital_id}: {details['time_minutes']} minutes, "
            f"{details['distance_km']:.1f} km, {details['mode']}"
        )
