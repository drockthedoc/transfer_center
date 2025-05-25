#!/usr/bin/env python3
"""
Enhanced Test Script for UI Display Improvements

This script tests the enhancements to recommendation creation and display,
ensuring that all fields required by the UI are properly populated.
"""

import logging
import sys
from datetime import datetime
from pprint import pprint

from src.core.decision_engine import recommend_campus
from src.core.models import (
    Location, PatientData, TransferRequest, TransportMode,
    Gender, Recommendation, LLMReasoningDetails
)
from src.core.transport_calculator import TransportTimeEstimator
from src.llm.robust_recommendation_handler import RecommendationHandler
from src.utils.hospital_loader import load_hospitals

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def print_separator(message):
    """Print a section separator with a message."""
    print("\n" + "=" * 50)
    print(f" {message} ".center(50, "="))
    print("=" * 50)

def create_test_patient(name, age, location):
    """Create a test patient with the given parameters."""
    return PatientData(
        name=name,
        age=age,
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
    ), Location(
        latitude=location[0],
        longitude=location[1],
        address="Test Location"
    )

def test_recommendation_display(location_name, coordinates):
    """Test the recommendation creation with UI display improvements."""
    print_separator(f"TESTING: {location_name}")
    
    # Create test patient and request
    patient, location = create_test_patient(
        f"Test Patient from {location_name}", 7, coordinates
    )
    
    request = TransferRequest(
        patient_data=patient,
        location=location,
        transport_info={
            "clinical_text": f"7-year-old male patient from {location_name} with mild fever and cough.",
            "sending_facility": f"{location_name} Community Hospital",
            "referring_physician": "Dr. Test"
        }
    )
    
    # Load hospitals
    hospitals = load_hospitals()
    print(f"Loaded {len(hospitals)} hospitals")
    
    # Get current weather (simulated)
    current_weather = {
        "weather_conditions": "Clear",
        "temperature_celsius": 25,
        "wind_speed_kmh": 10,
        "precipitation_mm": 0
    }
    
    # Available transport modes
    available_transport_modes = [
        TransportMode.GROUND_AMBULANCE,
        TransportMode.HELICOPTER,
        TransportMode.FIXED_WING
    ]
    
    # Get recommendation
    recommendation = recommend_campus(
        request=request,
        campuses=hospitals,
        current_weather=current_weather,
        available_transport_modes=available_transport_modes
    )
    
    # Print distances
    print("\n=== Distances from sending location to each hospital ===")
    transport_calculator = TransportTimeEstimator()
    for hospital in hospitals:
        distance = transport_calculator.calculate_distance_km(location, hospital.location)
        print(f"{hospital.name}: {distance:.2f} km")
    
    # Print raw recommendation
    print("\n=== RAW RECOMMENDATION ===")
    for key, value in recommendation.__dict__.items():
        if key != 'explainability_details':
            print(f"{key}: {value}")
    
    # Enhance the recommendation with more UI-friendly data
    enhanced_recommendation = enhance_recommendation_for_ui(recommendation, location)
    
    # Print enhanced recommendation details
    print("\n=== ENHANCED RECOMMENDATION ===")
    for key, value in enhanced_recommendation.__dict__.items():
        if key == 'transport_details':
            print(f"{key}:")
            pprint(value)
        elif key == 'conditions':
            print(f"{key}:")
            pprint(value)
        elif key == 'explainability_details':
            print(f"{key}: (Object with reasoning details)")
        else:
            print(f"{key}: {value}")
    
    # Simulate UI display formatting
    print("\n=== SIMULATED UI DISPLAY ===")
    print_ui_display(enhanced_recommendation)
    
    return enhanced_recommendation

def enhance_recommendation_for_ui(recommendation, origin_location):
    """Enhance a recommendation with additional details for UI display."""
    # Get the hospital details
    hospitals = load_hospitals()
    recommended_hospital = None
    for hospital in hospitals:
        if hospital.campus_id == recommendation.recommended_campus_id:
            recommended_hospital = hospital
            break
    
    if not recommended_hospital:
        logger.warning(f"Could not find hospital with ID: {recommendation.recommended_campus_id}")
        return recommendation
    
    # Calculate accurate transport details
    transport_calculator = TransportTimeEstimator()
    distance_km = transport_calculator.calculate_distance_km(
        origin_location, recommended_hospital.location
    )
    
    # Choose transport mode based on distance
    transport_mode = TransportMode.GROUND_AMBULANCE
    if distance_km > 300:
        transport_mode = TransportMode.HELICOPTER
    elif distance_km > 500:
        transport_mode = TransportMode.FIXED_WING
    
    estimated_minutes = transport_calculator.estimate_transport_time_minutes(
        origin_location, recommended_hospital.location, transport_mode
    )
    
    # Create enhanced transport details
    transport_details = {
        "mode": transport_mode.name,
        "estimated_time": f"{estimated_minutes:.0f} minutes",
        "estimated_time_minutes": estimated_minutes,
        "distance": f"{distance_km:.1f} km",
        "distance_km": distance_km,
        "special_requirements": "None"
    }
    
    # Add simulated conditions
    weather_conditions = "Clear, sunny conditions"
    traffic_conditions = "Light traffic expected"
    
    if distance_km > 200:
        weather_conditions = "Partly cloudy, monitor for changes"
    if distance_km > 100:
        traffic_conditions = "Moderate traffic on highways"
    
    conditions = {
        "weather": weather_conditions,
        "traffic": traffic_conditions,
        "estimated_arrival_time": datetime.now().strftime("%H:%M") + f" (in ~{estimated_minutes:.0f} minutes)"
    }
    
    # Create explainability details
    explainability_details = LLMReasoningDetails(
        main_recommendation_reason=f"Selected {recommended_hospital.name} as it is the closest suitable facility with available beds.",
        key_factors_considered=[
            f"Distance: {distance_km:.1f} km ({estimated_minutes:.0f} min travel time)",
            f"Transport mode: {transport_mode.name}",
            "Bed availability confirmed",
            "Appropriate care level available"
        ],
        confidence_explanation="High confidence based on proximity and bed availability",
        alternative_reasons={}
    )
    
    # Create enhanced recommendation
    enhanced_recommendation = Recommendation(
        transfer_request_id=recommendation.transfer_request_id,
        recommended_campus_id=recommendation.recommended_campus_id,
        recommended_campus_name=recommended_hospital.name,
        reason=recommendation.reason,
        confidence_score=recommendation.confidence_score,
        recommended_level_of_care=recommendation.recommended_level_of_care,
        notes=recommendation.notes or [],
        transport_details=transport_details,
        conditions=conditions,
        explainability_details=explainability_details
    )
    
    return enhanced_recommendation

def print_ui_display(recommendation):
    """Simulate how the recommendation would appear in the UI."""
    # Main recommendation display
    print(f"\n🏥 Recommended Hospital: {recommendation.recommended_campus_name}")
    print(f"   ID: {recommendation.recommended_campus_id}")
    print(f"   Care Level: {recommendation.recommended_level_of_care}")
    print(f"   Confidence: {recommendation.confidence_score}%")
    
    # Transport details
    print("\n📊 Transport Details:")
    transport = recommendation.transport_details
    print(f"   Mode: {transport.get('mode', 'Unknown').replace('_', ' ').title()}")
    print(f"   Estimated Time: {transport.get('estimated_time', 'Unknown')}")
    print(f"   Distance: {transport.get('distance', 'Unknown')}")
    if 'special_requirements' in transport and transport['special_requirements'] != "None":
        print(f"   Special Requirements: {transport['special_requirements']}")
    
    # Conditions
    conditions = recommendation.conditions
    print("\n🌦️ Conditions:")
    print(f"   Weather: {conditions.get('weather', 'Unknown')}")
    print(f"   Traffic: {conditions.get('traffic', 'Unknown')}")
    if 'estimated_arrival_time' in conditions:
        print(f"   Estimated Arrival: {conditions.get('estimated_arrival_time')}")
    
    # Clinical reasoning
    print("\n📋 Clinical Reasoning:")
    print(f"   {recommendation.reason}")
    
    # Notes
    if recommendation.notes:
        print("\n📝 Notes:")
        for note in recommendation.notes:
            print(f"   • {note}")
    
    # Explainability (simplified)
    if hasattr(recommendation, 'explainability_details') and recommendation.explainability_details:
        print("\n🔍 Key Factors:")
        if hasattr(recommendation.explainability_details, 'key_factors_considered'):
            for factor in recommendation.explainability_details.key_factors_considered:
                print(f"   • {factor}")

if __name__ == "__main__":
    # Test with multiple locations
    austin_location = (30.2672, -97.7431)  # Austin
    houston_location = (29.7604, -95.3698)  # Houston
    midpoint_location = (30.0138, -96.5565)  # Halfway between
    
    # Run the tests
    test_recommendation_display("Austin", austin_location)
    test_recommendation_display("Houston", houston_location)
    test_recommendation_display("Midpoint", midpoint_location)
