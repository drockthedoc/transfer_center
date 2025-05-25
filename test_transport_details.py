#!/usr/bin/env python3
"""
Simple test to verify transport details are in the recommendation object.
"""

import sys
from src.core.decision_engine import recommend_campus
from src.core.models import Location, PatientData, TransferRequest, TransportMode, Gender
from src.utils.hospital_loader import load_hospitals

# Create a test patient in Austin
patient = PatientData(
    name="Test Patient",
    age=7,
    gender=Gender.MALE,
    weight_kg=25,
    height_cm=120,
    vital_signs={
        "heart_rate": 90,
        "respiratory_rate": 20,
        "temperature_celsius": 37.0,
        "blood_pressure": "110/70",
        "oxygen_saturation": 99
    }
)

# Create a location in Austin
location = Location(
    latitude=30.2672,
    longitude=-97.7431,
    address="Austin, TX"
)

# Create a transfer request
request = TransferRequest(
    patient_data=patient,
    location=location,
    transport_info={
        "clinical_text": "7-year-old male patient with mild fever and cough.",
        "sending_facility": "Austin Community Hospital",
        "referring_physician": "Dr. Test"
    }
)

# Get available hospitals
hospitals = load_hospitals()
print(f"Loaded {len(hospitals)} hospitals")

# Simulate weather data
current_weather = {
    "weather_conditions": "Clear",
    "temperature_celsius": 25,
    "wind_speed_kmh": 10,
    "precipitation_mm": 0
}

# Available transport modes
transport_modes = [
    TransportMode.GROUND_AMBULANCE,
    TransportMode.HELICOPTER,
    TransportMode.FIXED_WING
]

# Get recommendation
recommendation = recommend_campus(
    request=request,
    campuses=hospitals,
    current_weather=current_weather,
    available_transport_modes=transport_modes
)

# Print raw object details
print("\n\n=== FULL RECOMMENDATION OBJECT DUMP ===")
for key, value in vars(recommendation).items():
    print(f"{key}: {value}")

# Check if transport_details exists and what's in it
print("\n=== TRANSPORT DETAILS CONTENT ===")
transport_details = getattr(recommendation, 'transport_details', None)
if transport_details:
    print(f"Type: {type(transport_details)}")
    if isinstance(transport_details, dict):
        for key, value in transport_details.items():
            print(f"  {key}: {value}")
    else:
        print(f"Value: {transport_details}")
else:
    print("No transport_details attribute found")
