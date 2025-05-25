#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Direct test of the recommendation engine without using the GUI.
Tests hospital proximity calculations and recommendations.
"""

import logging
import os
import sys
from datetime import datetime

from src.core.models import (
    Location,
    PatientData,
    TransferRequest,
    TransportMode,
    WeatherData,
)
from src.core.decision_engine import recommend_campus
import json
from pathlib import Path
from src.utils.geolocation import calculate_distance

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_hospital_recommendations(sending_location, care_level="PICU"):
    """Test hospital recommendations from a specific sending location."""
    
    # Load available hospitals
    hospital_data_path = os.path.join("data", "sample_hospital_campuses.json")
    with open(hospital_data_path, "r") as f:
        hospitals_data = json.load(f)
    
    # Convert to hospital campus objects
    from src.core.models import HospitalCampus, BedCensus
    hospitals = []
    for data in hospitals_data:
        location = Location(latitude=data["location"]["latitude"], longitude=data["location"]["longitude"])
        bed_census = BedCensus(
            total_beds=data.get("bed_census", {}).get("total_beds", 100),
            available_beds=data.get("bed_census", {}).get("available_beds", 20),
            icu_beds_total=data.get("bed_census", {}).get("icu_beds_total", 30),
            icu_beds_available=data.get("bed_census", {}).get("icu_beds_available", 10),
            nicu_beds_total=data.get("bed_census", {}).get("nicu_beds_total", 20),
            nicu_beds_available=data.get("bed_census", {}).get("nicu_beds_available", 5)
        )
        hospital = HospitalCampus(
            campus_id=data["campus_id"],
            name=data["name"],
            location=location,
            metro_area=data.get("metro_area", "UNKNOWN"),
            address=data.get("address", ""),
            exclusions=data.get("exclusions", []),
            bed_census=bed_census
        )
        hospitals.append(hospital)
    
    # Create a dummy patient
    patient = PatientData(
        patient_id="TEST123",
        clinical_text="3-year-old with respiratory distress",
        extracted_data={
            "demographics": {"age": 3, "gender": "male"},
            "vital_signs": {
                "heart_rate": 145,
                "respiratory_rate": 35,
                "blood_pressure": "90/60",
                "temperature": 39.5,
                "o2_saturation": "93%"
            }
        },
        care_needs=["respiratory support", "critical care"],
        care_level=care_level
    )
    
    # Create a transfer request
    request = TransferRequest(
        request_id=f"REQ_TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        patient_data=patient,
        clinical_notes="3-year-old male with respiratory distress, fever, and history of prematurity",
        sending_location=sending_location,
        requested_datetime=datetime.now(),
        transport_info={
            "preferred_mode": "ANY",
            "notes": "Test transport request"
        }
    )
    
    # Mock weather data
    weather = WeatherData(
        temperature_celsius=24,  # 75F in Celsius
        wind_speed_kph=8,       # 5mph in kph
        visibility_km=16,       # 10 miles in km
        weather_condition="CLEAR"
    )
    
    # Available transport modes
    transport_modes = [
        TransportMode.GROUND_AMBULANCE,
        TransportMode.HELICOPTER,
        TransportMode.FIXED_WING
    ]
    
    # Call the recommendation engine
    recommendation = recommend_campus(
        request=request,
        campuses=hospitals,
        current_weather=weather,
        available_transport_modes=transport_modes
    )
    
    # Print the distances from sending location to each hospital
    print("\n=== Distances from sending location to each hospital ===")
    for hospital in hospitals:
        dist = calculate_distance(sending_location, hospital.location)
        print(f"{hospital.name}: {dist:.2f} km")
    
    # Display recommendation result
    if recommendation:
        print("\n=== RECOMMENDATION RESULT ===")
        # Extract transport mode and time from reason string since we know it's there
        import re
        
        # Get hospital name
        for hospital in hospitals:
            if hospital.campus_id == recommendation.recommended_campus_id:
                hospital_name = hospital.name
                break
        else:
            hospital_name = "Unknown Hospital"
            
        # Extract travel time and mode from reason string
        time_match = re.search(r'(\d+\.\d+) minutes by ([\w\.]+)', recommendation.reason)
        if time_match:
            travel_time = time_match.group(1)
            transport_mode = time_match.group(2)
        else:
            travel_time = "Unknown"
            transport_mode = "Not specified"
            
        print(f"Recommended hospital: {hospital_name}")
        print(f"Recommended hospital ID: {recommendation.recommended_campus_id}")
        print(f"Care level: {recommendation.recommended_level_of_care}")
        print(f"Reason: {recommendation.reason}")
        print(f"Transport mode: {transport_mode}")
        print(f"Estimated travel time: {travel_time} minutes")
        print(f"Special requirements: None")
        print(f"Distance to hospital: {calculate_distance(sending_location, hospital.location):.2f} km")
        print(f"Confidence score: {recommendation.confidence_score}")
    else:
        print("\n=== NO RECOMMENDATION AVAILABLE ===")
    
    return recommendation


if __name__ == "__main__":
    print("\n=== TESTING HOSPITAL RECOMMENDATIONS ===\n")
    
    # Test case 1: Sending location near Houston
    print("\n>>> TEST CASE 1: Patient in Houston area")
    houston_location = Location(latitude=29.7604, longitude=-95.3698)  # Downtown Houston
    test_hospital_recommendations(houston_location)
    
    # Test case 2: Sending location near Austin
    print("\n>>> TEST CASE 2: Patient in Austin area")
    austin_location = Location(latitude=30.2672, longitude=-97.7431)  # Downtown Austin
    test_hospital_recommendations(austin_location)
    
    # Test case 3: Sending location halfway between Houston and Austin
    print("\n>>> TEST CASE 3: Patient halfway between Houston and Austin")
    halfway_location = Location(latitude=30.0138, longitude=-96.5565)  # Roughly halfway
    test_hospital_recommendations(halfway_location)
