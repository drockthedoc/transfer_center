"""
Transport time estimator for the Transfer Center GUI.

This module handles the estimation of transport times between locations based on
different transport modes, traffic patterns, and specialized transport services.
"""
import math
import random
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from src.core.models import Location, TransportMode, HospitalCampus


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
            "houston": Location(latitude=29.7604, longitude=-95.3698),  # Texas Children's Hospital
            "austin": Location(latitude=30.2672, longitude=-97.7431)    # Austin base
        }
        
        # Average speeds for different transport modes (km/h)
        self.speeds = {
            "ground": 80.0,       # Average ground ambulance speed
            "helicopter": 240.0,  # Average helicopter speed
            "fixed_wing": 450.0,  # Average fixed-wing aircraft speed
            "pov": 70.0           # Average private vehicle speed
        }
        
        # Traffic patterns by time of day (multiplier on travel time)
        self.traffic_patterns = {
            # Houston traffic patterns (24-hour based, index 0 = midnight)
            "houston": [
                0.8, 0.7, 0.6, 0.6, 0.7, 0.9, 1.4, 1.8, 1.7, 1.4, 1.2, 1.3, 
                1.4, 1.3, 1.2, 1.3, 1.5, 1.8, 1.7, 1.4, 1.2, 1.0, 0.9, 0.8
            ],
            # Austin traffic patterns
            "austin": [
                0.7, 0.6, 0.6, 0.6, 0.7, 1.0, 1.5, 1.9, 1.8, 1.3, 1.1, 1.2,
                1.3, 1.2, 1.1, 1.2, 1.4, 1.9, 1.8, 1.4, 1.2, 1.0, 0.9, 0.8
            ]
        }
    
    def _calculate_distance(self, loc1: Location, loc2: Location) -> float:
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
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        
        return distance
    
    def _get_metro_area(self, location: Location) -> str:
        """
        Determine which metro area a location is in (or closest to).
        
        Args:
            location: The location to check
            
        Returns:
            "houston" or "austin" based on proximity
        """
        dist_to_houston = self._calculate_distance(location, self.houston_center)
        dist_to_austin = self._calculate_distance(location, self.austin_center)
        
        return "houston" if dist_to_houston < dist_to_austin else "austin"
    
    def _get_current_traffic_factor(self, metro_area: str, eta_minutes: Optional[int] = None) -> float:
        """
        Get the current traffic factor based on time of day and metro area.
        
        Args:
            metro_area: "houston" or "austin"
            eta_minutes: Minutes until ETA (if specified)
            
        Returns:
            Traffic factor multiplier
        """
        # If we have a specific ETA, calculate traffic for that time
        if eta_minutes is not None:
            current_time = datetime.now()
            current_hour = current_time.hour
            current_minute = current_time.minute
            
            # Calculate the hour at ETA
            total_minutes = current_hour * 60 + current_minute + eta_minutes
            eta_hour = (total_minutes // 60) % 24
            
            return self.traffic_patterns.get(metro_area, self.traffic_patterns["houston"])[eta_hour]
        
        # Otherwise use current time
        current_hour = datetime.now().hour
        return self.traffic_patterns.get(metro_area, self.traffic_patterns["houston"])[current_hour]
    
    def _calculate_kangaroo_crew_time(
        self, 
        sending_location: Location, 
        receiving_location: Location,
        mode: str = "ground"
    ) -> Tuple[float, str]:
        """
        Calculate transport time using Kangaroo Crew, accounting for crew dispatch.
        
        Args:
            sending_location: Location of sending facility
            receiving_location: Location of receiving hospital
            mode: Transport mode ("ground", "helicopter", or "fixed_wing")
            
        Returns:
            Tuple of (time_in_minutes, notes)
        """
        # Determine which KC base to use based on location
        sending_metro = self._get_metro_area(sending_location)
        receiving_metro = self._get_metro_area(receiving_location)
        
        kc_base = self.kc_bases[sending_metro]
        
        # Calculate distances
        base_to_sender = self._calculate_distance(kc_base, sending_location)
        sender_to_receiver = self._calculate_distance(sending_location, receiving_location)
        
        # KC crew preparation time
        prep_time_minutes = 15  # Base preparation time
        
        # Account for cross-metro logistics (if sending and receiving in different metros)
        cross_metro = sending_metro != receiving_metro
        cross_metro_factor = 1.2 if cross_metro else 1.0
        
        # Calculate transport times based on mode
        if mode == "ground":
            # Base to sender time (KC crew traveling to pick up patient)
            base_to_sender_time = (base_to_sender / self.speeds["ground"]) * 60
            
            # Sender to receiver time (KC crew transporting patient)
            sender_to_receiver_time = (sender_to_receiver / self.speeds["ground"]) * 60
            
            # KC ground transport additional logistics time
            # (patient loading/unloading, documentation, etc.)
            logistics_time = 20
            
            total_time = (prep_time_minutes + base_to_sender_time + 
                          sender_to_receiver_time + logistics_time) * cross_metro_factor
            
            notes = f"KC Ground: {prep_time_minutes:.0f}min prep + {base_to_sender_time:.0f}min to patient + {sender_to_receiver_time:.0f}min transport"
            
        elif mode == "helicopter":
            # Helicopter preparation and startup
            heli_prep_time = 20
            
            # Base to sender time (KC helicopter traveling to pick up)
            base_to_sender_time = (base_to_sender / self.speeds["helicopter"]) * 60
            
            # Sender to receiver time (helicopter transport with patient)
            sender_to_receiver_time = (sender_to_receiver / self.speeds["helicopter"]) * 60
            
            # Helicopter logistics (landing, patient loading/unloading, etc.)
            logistics_time = 25
            
            total_time = (prep_time_minutes + heli_prep_time + base_to_sender_time + 
                          sender_to_receiver_time + logistics_time) * cross_metro_factor
            
            notes = f"KC Helicopter: {prep_time_minutes + heli_prep_time:.0f}min prep + {base_to_sender_time:.0f}min to patient + {sender_to_receiver_time:.0f}min transport"
            
        else:  # fixed_wing
            # Fixed-wing preparation and startup
            plane_prep_time = 30
            
            # Fixed-wing can only operate between airports, so we need to account for:
            # 1. Ground transport from base to airport (if not at airport)
            # 2. Flight time between airports
            # 3. Ground transport from arrival airport to receiving hospital
            
            # For this simulation, we'll use simplified assumptions
            airport_logistics_time = 45  # Time for airport procedures, boarding, etc.
            
            # Flight time (direct distance / speed)
            flight_time = (sender_to_receiver / self.speeds["fixed_wing"]) * 60
            
            # Ground transport to/from airports (estimated)
            ground_transport_time = 30
            
            total_time = (prep_time_minutes + plane_prep_time + airport_logistics_time + 
                          flight_time + ground_transport_time) * cross_metro_factor
            
            notes = f"KC Fixed-Wing: {prep_time_minutes + plane_prep_time:.0f}min prep + {airport_logistics_time:.0f}min airport logistics + {flight_time:.0f}min flight"
        
        return total_time, notes
    
    def estimate_transport_times(
        self,
        sending_location: Location,
        hospitals: List[HospitalCampus],
        transport_modes: List[TransportMode],
        minutes_until_eta: Optional[int] = None,
        transport_type: str = "Local EMS",
        kc_mode: str = "ground"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Estimate transport times from sending location to all hospitals.
        
        Args:
            sending_location: Location of sending facility
            hospitals: List of potential receiving hospitals
            transport_modes: Available transport modes
            minutes_until_eta: Minutes until expected arrival time (optional)
            transport_type: Type of transport ("POV", "Local EMS", or "Kangaroo Crew")
            kc_mode: Kangaroo Crew mode if applicable ("ground", "helicopter", "fixed_wing")
            
        Returns:
            Dictionary mapping hospital IDs to transport details:
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
        results = {}
        
        # Sending facility metro area for traffic patterns
        sending_metro = self._get_metro_area(sending_location)
        
        # Get traffic factor if applicable
        traffic_factor = self._get_current_traffic_factor(
            sending_metro, 
            eta_minutes
        ) if transport_type in ["POV (Private Vehicle)", "Local EMS"] else 1.0
        
        for hospital in hospitals:
            # Calculate base distance
            distance = self._calculate_distance(sending_location, hospital.location)
            
            # Initialize with worst-case values
            best_time = float('inf')
            best_mode = None
            best_notes = ""
            
            # If Kangaroo Crew is the transport type, use the KC calculation
            if transport_type == "Kangaroo Crew":
                kc_time, kc_notes = self._calculate_kangaroo_crew_time(
                    sending_location, 
                    hospital.location,
                    kc_mode
                )
                
                best_time = kc_time
                best_mode = f"Kangaroo Crew ({kc_mode})"
                best_notes = kc_notes
                
            # Otherwise evaluate all allowed transport modes
            else:
                for mode in transport_modes:
                    if mode == TransportMode.GROUND_AMBULANCE:
                        # Use appropriate speed based on transport type
                        if transport_type == "POV (Private Vehicle)":
                            speed_key = "pov"
                        else:  # Local EMS
                            speed_key = "ground"
                            
                        # Calculate time with traffic
                        time_hours = (distance / self.speeds[speed_key]) * traffic_factor
                        time_minutes = time_hours * 60
                        
                        mode_str = transport_type
                        notes = f"Traffic factor: {traffic_factor:.2f}x"
                        
                    elif mode == TransportMode.AIR_AMBULANCE:
                        # We'll assume air ambulance is unaffected by ground traffic
                        time_hours = distance / self.speeds["helicopter"]
                        time_minutes = time_hours * 60
                        
                        # Add logistics time for helicopter transport
                        time_minutes += 30  # Extra time for takeoff, landing, patient transfer
                        
                        mode_str = "Helicopter"
                        notes = "Air medical transport"
                    
                    # Check if this mode is better than current best
                    if time_minutes < best_time:
                        best_time = time_minutes
                        best_mode = mode_str
                        best_notes = notes
            
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
                "traffic_factor": traffic_factor if "traffic_factor" in best_notes else 1.0,
                "notes": best_notes
            }
        
        return results


# Example usage when run directly
if __name__ == "__main__":
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
                "nicu_beds_available": 8
            },
            exclusions=[],
            helipads=[]
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
                "nicu_beds_available": 4
            },
            exclusions=[],
            helipads=[]
        )
    ]
    
    # Estimate transport times
    print("Example Transport Time Estimation:")
    
    # Local EMS
    print("\nLocal EMS:")
    local_ems_times = estimator.estimate_transport_times(
        sending,
        hospitals,
        [TransportMode.GROUND_AMBULANCE],
        transport_type="Local EMS"
    )
    for hospital_id, details in local_ems_times.items():
        print(f"{hospital_id}: {details['time_minutes']} minutes, {details['distance_km']:.1f} km, {details['mode']}")
    
    # Kangaroo Crew (ground)
    print("\nKangaroo Crew (ground):")
    kc_ground_times = estimator.estimate_transport_times(
        sending,
        hospitals,
        [],  # Not used for KC
        transport_type="Kangaroo Crew",
        kc_mode="ground"
    )
    for hospital_id, details in kc_ground_times.items():
        print(f"{hospital_id}: {details['time_minutes']} minutes, {details['distance_km']:.1f} km, {details['mode']}")
    
    # Kangaroo Crew (helicopter)
    print("\nKangaroo Crew (helicopter):")
    kc_heli_times = estimator.estimate_transport_times(
        sending,
        hospitals,
        [],  # Not used for KC
        transport_type="Kangaroo Crew",
        kc_mode="helicopter"
    )
    for hospital_id, details in kc_heli_times.items():
        print(f"{hospital_id}: {details['time_minutes']} minutes, {details['distance_km']:.1f} km, {details['mode']}")
