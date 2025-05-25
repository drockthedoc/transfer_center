"""
Main decision engine for the Transfer Center.

This module contains the core decision logic for recommending hospital campuses
for patient transfers, integrating exclusion checking and transport evaluation.
"""

import logging
import sys
from typing import Any, Dict, List, Optional

from src.core.decision.exclusion_checker import check_patient_exclusions
from src.core.decision.transport_evaluation import (
    calculate_total_transport_time,
    evaluate_transport_options,
)
from src.core.models import (
    HospitalCampus,
    PatientData,
    Recommendation,
    TransferRequest,
    TransportMode,
    WeatherData,
)
from src.explainability.explainer import generate_simple_explanation, FALLBACK_REASONING

logger = logging.getLogger(__name__)


def recommend_campus(
    request: TransferRequest,
    campuses: List[HospitalCampus],
    current_weather: WeatherData,
    available_transport_modes: List[TransportMode],
    transport_time_estimates: Optional[Dict[str, Dict[str, Any]]] = None,
    human_suggestions: Optional[Dict[str, Any]] = None,
) -> Optional[Recommendation]:
    """
    Recommend the best hospital campus for a transfer request.

    Args:
        request: Transfer request with patient data and sending location
        campuses: List of potential hospital campuses
        current_weather: Current weather data
        available_transport_modes: List of available transport modes
        transport_time_estimates: Optional pre-calculated transport time estimates
        human_suggestions: Optional human suggestions to consider

    Returns:
        Recommendation object or None if no suitable campus found
    """
    # Setup debug logging to stdout
    print("\n\n!!!!!!!!! RECOMMENDATION ENGINE STARTED !!!!!!!!!")
    sys.stdout.flush()

    # Check for valid campuses
    if not campuses:
        print("!!! No campuses provided !!!")
        sys.stdout.flush()
        return None

    # STEP 1: Check exclusions for each campus
    print(f"STEP 1: Checking {len(campuses)} campuses for exclusions")
    sys.stdout.flush()

    eligible_campuses = []
    for campus in campuses:
        exclusions = check_patient_exclusions(request.patient_data, campus)
        if not exclusions:
            eligible_campuses.append(campus)
            print(f"Campus {campus.name} passed exclusion checks")
        else:
            print(f"Campus {campus.name} excluded: {[e.name for e in exclusions]}")
    sys.stdout.flush()

    if not eligible_campuses:
        print("!!! No eligible campuses after exclusion checks !!!")
        sys.stdout.flush()
        return None

    # STEP 2: Check bed availability
    print(f"\nSTEP 2: Checking {len(eligible_campuses)} campuses for bed availability")
    sys.stdout.flush()

    # Extract care level requirements from human suggestions
    care_levels = []
    if human_suggestions and "care_levels" in human_suggestions:
        care_levels = human_suggestions["care_levels"]
        print(f"Care levels requested: {care_levels}")

    campuses_with_beds = []
    for campus in eligible_campuses:
        print(f"Checking beds for {campus.name}")
        if "ICU" in care_levels or "PICU" in care_levels:
            if campus.bed_census.icu_beds_available > 0:
                campuses_with_beds.append(
                    {
                        "campus": campus,
                        "bed_type": "ICU/PICU",
                        "beds_available": campus.bed_census.icu_beds_available,
                    }
                )
                print(f"  Has {campus.bed_census.icu_beds_available} ICU/PICU beds")
        elif "NICU" in care_levels:
            if campus.bed_census.nicu_beds_available > 0:
                campuses_with_beds.append(
                    {
                        "campus": campus,
                        "bed_type": "NICU",
                        "beds_available": campus.bed_census.nicu_beds_available,
                    }
                )
                print(f"  Has {campus.bed_census.nicu_beds_available} NICU beds")
        else:
            if campus.bed_census.available_beds > 0:
                campuses_with_beds.append(
                    {
                        "campus": campus,
                        "bed_type": "General",
                        "beds_available": campus.bed_census.available_beds,
                    }
                )
                print(f"  Has {campus.bed_census.available_beds} general beds")
    sys.stdout.flush()

    if not campuses_with_beds:
        print("!!! No eligible campuses with available beds !!!")
        sys.stdout.flush()
        return None

    # STEP 3: Evaluate transport options
    print(
        f"\nSTEP 3: Evaluating transport options for {len(campuses_with_beds)} campuses"
    )
    sys.stdout.flush()

    campuses_with_distance = []
    for campus_data in campuses_with_beds:
        campus = campus_data["campus"]
        print(f"Evaluating transport to {campus.name}")

        # Get best transport mode and time
        transport_mode, travel_minutes = evaluate_transport_options(
            request.sending_location,
            campus,
            available_transport_modes,
            current_weather,
            transport_time_estimates,
        )

        if transport_mode and travel_minutes:
            campuses_with_distance.append(
                {
                    "campus": campus,
                    "bed_type": campus_data["bed_type"],
                    "beds_available": campus_data["beds_available"],
                    "transport_mode": transport_mode,
                    "travel_time_minutes": travel_minutes,
                }
            )
            print(f"  Best option: {transport_mode}, {travel_minutes:.1f} minutes")
        else:
            print(f"  No viable transport option found")
    sys.stdout.flush()

    # If no campuses with valid travel options, return None
    if not campuses_with_distance:
        print(f"DEBUG: No campuses with valid travel routes found.")
        return None

    print(
        f"DEBUG: Found {len(campuses_with_distance)} campuses with valid travel routes"
    )

    # STEP 4: Sort by travel time (closest first)
    campuses_with_distance.sort(key=lambda x: x["travel_time_minutes"])
    print(
        f"DEBUG: Sorted campuses by travel time: "
        f"{[(c['campus'].name, c['travel_time_minutes']) for c in campuses_with_distance]}"
    )

    # STEP 5: Select the best campus (closest with available beds)
    if campuses_with_distance:
        best_option = campuses_with_distance[0]
        chosen_campus = best_option["campus"]
        print(
            f"DEBUG: Selected best campus: {chosen_campus.name} with "
            f"travel time {best_option['travel_time_minutes']} minutes"
        )
    else:
        print(
            "DEBUG: CRITICAL ERROR - No campuses with distance available despite earlier check"
        )
        return None

    # STEP 6: Generate explanation and recommendation
    # Prepare explanation notes
    notes = [
        f"Campus passed exclusion checks",
        f"Bed type: {best_option['bed_type']}, {best_option['beds_available']} available",
        f"Transport mode: {best_option['transport_mode']}, "
        f"travel time: {best_option['travel_time_minutes']:.1f} minutes",
        f"Selected as closest eligible campus with available beds",
    ]

    # Create explanation
    try:
        print(f"DEBUG: Generating explanation for {chosen_campus.name}")
        # Prepare a draft Recommendation object for generate_simple_explanation
        draft_recommendation_for_simple_explanation = Recommendation(
            transfer_request_id=request.request_id,
            recommended_campus_id=chosen_campus.campus_id,
            recommended_campus_name=chosen_campus.name, # Used by generate_simple_explanation
            reason="Draft reason for simple explanation generation.", # Placeholder
            explainability_details=FALLBACK_REASONING, # Not used by simple, but good practice
            notes=notes, # Used by generate_simple_explanation
            final_travel_time_minutes=best_option["travel_time_minutes"], # Used by generate_simple_explanation
            chosen_transport_mode=best_option["transport_mode"], # Used by generate_simple_explanation
            # Other fields can be default or None as they are not directly used by generate_simple_explanation
            confidence_score=0.0, # Placeholder
            recommended_level_of_care=request.patient_data.care_level or "Unknown", # Placeholder
            simple_explanation={}, # Will be populated by the function itself if it were modifying
            transport_details={}, # Placeholder
            conditions={}, # Placeholder
            scoring_results=[] # Placeholder
        )

        simple_explanation_output = generate_simple_explanation(
            recommendation=draft_recommendation_for_simple_explanation,
            patient_data=request.patient_data
        )
        print(f"DEBUG: Generated simple explanation output: {simple_explanation_output}")
    except Exception as e:
        print(f"ERROR: Failed to generate simple explanation: {e}")
        # Fallback for simple_explanation_output if generation fails
        simple_explanation_output = {
            "recommended_campus_name": chosen_campus.name,
            "key_factors_for_recommendation": [
                f"Error generating detailed simple explanation: {e}"
            ],
            "other_considerations_from_notes": notes or []
        }
        print(f"DEBUG: Using fallback simple explanation output: {simple_explanation_output}")

    # Create final recommendation
    try:
        print(f"DEBUG: Creating recommendation object")
        recommendation_reason = (
            f"Campus {chosen_campus.name} selected: passed exclusion checks, "
            f"has {best_option['beds_available']} {best_option['bed_type']} beds available, "
            f"and is the closest eligible campus at "
            f"{best_option['travel_time_minutes']:.1f} minutes by {best_option['transport_mode']}."
        )
        print(f"DEBUG: Recommendation reason: {recommendation_reason}")

        recommendation = Recommendation(
            transfer_request_id=request.request_id,
            recommended_campus_id=chosen_campus.campus_id,
            reason=recommendation_reason,
            confidence_score=100.0,  # Simple algorithm is deterministic
            explainability_details=FALLBACK_REASONING, # This path does not use LLM for these details
            notes=notes,
            simple_explanation=simple_explanation_output, # Use the generated dictionary
            recommended_campus_name=chosen_campus.name, # Ensure this is explicitly set
            final_travel_time_minutes=best_option["travel_time_minutes"],
            chosen_transport_mode=best_option["transport_mode"],
            recommended_level_of_care=request.patient_data.care_level or "General" # Match simple explanation
        )
        print(f"DEBUG: Successfully created recommendation: {recommendation}")
        print(
            f"Recommendation: {chosen_campus.name}. "
            f"Travel: {best_option['travel_time_minutes']:.1f} min via {best_option['transport_mode']}."
        )
        return recommendation
    except Exception as e:
        print(f"ERROR: Failed to create recommendation: {e}")
        print(f"DEBUG: Request ID: {request.request_id}")
        print(f"DEBUG: Campus ID: {chosen_campus.campus_id}")
        print(f"DEBUG: Notes: {notes}")
        return None
