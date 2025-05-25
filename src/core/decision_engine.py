"""
Decision Engine for the Transfer Center.

This module contains the core decision logic for recommending hospital campuses
for patient transfers based on exclusions, bed availability, and distance.
"""

from typing import Any, Dict, List, Optional, Tuple

from src.core.models import (
    HospitalCampus,
    Location,
    PatientData,
    Recommendation,
    TransportMode,
    WeatherData,
    LLMReasoningDetails,
    BedAvailability, 
    TransportOption, 
    TransferRequest, 
    ScoringResult
)
from src.core.scoring.score_processor import process_patient_scores
from src.core.exclusion_checker import check_exclusions
from src.utils.travel_calculator import get_air_travel_info, get_road_travel_info
from src.utils.geolocation import calculate_distance
from src.explainability.explainer import (
    generate_simple_explanation,
    generate_llm_explanation, 
    FALLBACK_REASONING
)
import sys
import traceback
import logging

logger = logging.getLogger(__name__)

def recommend_campus(
    request: TransferRequest,
    campuses: List[HospitalCampus], 
    available_transport_modes: List[TransportMode],
    weather_data: Optional[WeatherData] = None,
    traffic_conditions: Optional[Dict[str, Any]] = None,
) -> Optional[Recommendation]:

    import sys
    import traceback

    print("\n\n!!!!!!!!! RECOMMENDATION ENGINE STARTED !!!!!!!!!")
    sys.stdout.flush()

    # Simple direct algorithm for debugging
    try:
        # Check for valid campuses
        if not campuses:
            print("!!! No campuses provided !!!")
            sys.stdout.flush()
            return None

        print(f"STEP 1: Checking {len(campuses)} campuses for exclusions")
        sys.stdout.flush()

        # Filter campuses by exclusions
        eligible_campuses = []
        for campus in campuses:
            exclusions = check_exclusions(request.patient_data, campus)
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

        print(
            f"\nSTEP 2: Checking {len(eligible_campuses)} campuses for bed availability"
        )
        sys.stdout.flush()

        # Filter campuses by bed availability
        care_levels = []
        score_justifications = []

        # Check if human suggestions have care levels
        human_suggestions_data = request.transport_info.get("human_suggestions", {})
        if human_suggestions_data and "care_levels" in human_suggestions_data:
            care_levels = human_suggestions_data["care_levels"]
            print(f"Care levels requested by human: {care_levels}")
        else:
            # Use scoring systems to determine care levels automatically
            print("No human care level suggestions, using automatic scoring systems")
            try:
                # Process patient scores to determine care level
                scoring_results_dict = process_patient_scores(request.patient_data)
                
                # Extract ScoringResult objects for the LLM explainer and store in TransferRequest
                if "scores" in scoring_results_dict and isinstance(scoring_results_dict["scores"], dict):
                    request.processed_scoring_results = [
                        item for item in scoring_results_dict["scores"].values() if isinstance(item, ScoringResult)
                    ]
                else:
                    request.processed_scoring_results = []
                
                care_levels = scoring_results_dict.get("recommended_care_levels", ["General"])
                score_justifications = scoring_results_dict.get("justifications", ["Default due to scoring error"])

                print(f"Automatically determined care levels: {care_levels}")
                print(f"Justifications: {score_justifications}")
                print(f"Processed {len(request.processed_scoring_results)} ScoringResult objects.")

                # Add scoring details to notes for transparency using the original dict structure
                if "scores" in scoring_results_dict and isinstance(scoring_results_dict["scores"], dict):
                    for score_name, score_data_obj in scoring_results_dict["scores"].items():
                        # score_data_obj here is expected to be a ScoringResult object
                        if isinstance(score_data_obj, ScoringResult) and score_data_obj.score_value is not None:
                            print(f"{score_data_obj.score_name.upper()} Score: {score_data_obj.score_value} ({score_data_obj.interpretation})")
                        elif isinstance(score_data_obj, dict): # Fallback for older dict structure if any
                             if score_data_obj != "N/A" and isinstance(score_data_obj.get("score"), (int, float)):
                                print(f"{score_name.upper()} Score: {score_data_obj['score']}")
            except Exception as e:
                print(f"Error using scoring systems: {str(e)}")
                print("Defaulting to General care level")
                care_levels = ["General"]
                score_justifications = ["Default due to scoring error"]

        campuses_with_beds = []
        for campus in eligible_campuses:
            print(f"Checking beds for {campus.name}")
            # Check ICU/PICU beds if needed
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
            print("!!! No campuses with available beds !!!")
            sys.stdout.flush()
            return None

        print(
            f"\nSTEP 3: Finding closest campus among {len(campuses_with_beds)} options"
        )
        sys.stdout.flush()

        # Prepare origin location
        sending_facility = request.sending_location or request.sending_facility_location
        print(f"Origin location: {sending_facility}")

        # Find closest campus
        transport_time_estimates = {} # Initialize the dictionary
        closest_campus_data = None
        closest_travel_time = float("inf")

        for campus_data in campuses_with_beds:
            campus = campus_data["campus"]
            print(f"Calculating travel time to {campus.name}")

            # Calculate fastest travel time
            min_travel_time = float("inf")
            best_mode = None

            # First check if we have pre-calculated time estimates
            if (
                transport_time_estimates
                and campus.campus_id in transport_time_estimates
            ):
                print(f"  Using pre-calculated time estimates for {campus.name}")
                campus_estimates = transport_time_estimates[campus.campus_id]

                # Ground travel
                if TransportMode.GROUND_AMBULANCE in available_transport_modes:
                    if (
                        "ground" in campus_estimates
                        and "duration_minutes" in campus_estimates["ground"]
                    ):
                        time_minutes = campus_estimates["ground"]["duration_minutes"]
                        print(f"  Ground travel (from estimates): {time_minutes:.1f} minutes")
                        if time_minutes < min_travel_time:
                            min_travel_time = time_minutes
                            best_mode = TransportMode.GROUND_AMBULANCE

                # Air travel
                if TransportMode.AIR_AMBULANCE in available_transport_modes:
                    if (
                        "air" in campus_estimates
                        and "duration_minutes" in campus_estimates["air"]
                    ):
                        time_minutes = campus_estimates["air"]["duration_minutes"]
                        print(f"  Air travel (from estimates): {time_minutes:.1f} minutes")
                        if time_minutes < min_travel_time:
                            min_travel_time = time_minutes
                            best_mode = TransportMode.AIR_AMBULANCE

            # If no pre-calculated estimates, try to calculate directly
            if min_travel_time == float("inf"):
                # Ground travel
                if TransportMode.GROUND_AMBULANCE in available_transport_modes:
                    try:
                        # Extract campus object properly from the dictionary data structure
                        campus_obj = campus_data["campus"]
                        road_info = get_road_travel_info(
                            sending_facility, campus_obj.location
                        )
                        if road_info and "duration_minutes" in road_info:
                            time_minutes = road_info["duration_minutes"]
                            print(f"  Ground travel: {time_minutes:.1f} minutes")
                            if time_minutes < min_travel_time:
                                min_travel_time = time_minutes
                                best_mode = TransportMode.GROUND_AMBULANCE
                    except Exception as e:
                        print(f"  Error calculating ground travel: {e}")

                # Air travel
                if TransportMode.AIR_AMBULANCE in available_transport_modes:
                    try:
                        if weather_data is None:
                            print("  Warning: Weather data is not available, cannot accurately assess air travel viability.")
                            # Optionally, consider air travel non-viable here or handle as per requirements
                        air_info = get_air_travel_info(
                            sending_facility,
                            campus_data["campus"].location,
                            weather_data,
                        )
                        if air_info and air_info.get("viable") and "duration_minutes" in air_info:
                            time_minutes = air_info["duration_minutes"]
                            print(f"  Air travel: {time_minutes:.1f} minutes")
                            if time_minutes < min_travel_time:
                                min_travel_time = time_minutes
                                best_mode = TransportMode.AIR_AMBULANCE
                    except Exception as e:
                        print(f"  Error calculating air travel: {e}")

            # If still no valid travel time, use a simple distance-based calculation
            # as fallback
            if min_travel_time == float("inf"):
                try:
                    print(f"  Using fallback distance calculation for {campus.name}")
                    # Simple calculation based on coordinates
                    lat1, lon1 = sending_facility.latitude, sending_facility.longitude
                    campus_obj = campus_data["campus"]
                    lat2, lon2 = (
                        campus_obj.location.latitude,
                        campus_obj.location.longitude,
                    )

                    # Haversine formula
                    import math

                    R = 6371  # Earth radius in km
                    dLat = math.radians(lat2 - lat1)
                    dLon = math.radians(lon2 - lon1)
                    a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.cos(
                        math.radians(lat1)
                    ) * math.cos(math.radians(lat2)) * math.sin(dLon / 2) * math.sin(
                        dLon / 2
                    )
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                    distance_km = R * c

                    # Assume average speed of 60 km/h for ground transport
                    time_minutes = distance_km / 60 * 60  # Convert to minutes
                    print(
                        f"  Fallback calculation: {distance_km:.1f} km, ~{time_minutes:.1f} minutes by ground"
                    )
                    min_travel_time = time_minutes
                    best_mode = TransportMode.GROUND_AMBULANCE
                except Exception as e:
                    print(f"  Error in fallback calculation: {e}")
                    # Last resort - assign an arbitrary travel time (4 hours) to ensure
                    # we have a result
                    min_travel_time = 240  # 4 hours in minutes
                    best_mode = TransportMode.GROUND_AMBULANCE
                    print(f"  Using default travel time of {min_travel_time} minutes")

            # With our fallback mechanisms, we should always have a travel option now
            if best_mode is None:
                print(
                    f"  WARNING: No travel mode selected for {campus.name} despite fallbacks"
                )
                # Final fallback - force a value
                best_mode = TransportMode.GROUND_AMBULANCE
                min_travel_time = 240  # 4 hours

            print(f"  Best travel: {min_travel_time:.1f} minutes via {best_mode}")

            # Check if this is the closest campus so far
            if min_travel_time < closest_travel_time:
                closest_travel_time = min_travel_time
                closest_campus_data = campus_data.copy()
                closest_campus_data["travel_time_minutes"] = min_travel_time
                closest_campus_data["transport_mode"] = best_mode
                print(f"  New closest campus: {campus.name}")
        sys.stdout.flush()

        if closest_campus_data is None:
            print("!!! No valid travel options to any campus !!!")
            sys.stdout.flush()
            return None

        # Create recommendation
        print(
            f"\nFINAL STEP: Creating recommendation for {closest_campus_data['campus'].name}"
        )
        campus: HospitalCampus = closest_campus_data["campus"] # This is the HospitalCampus object
        logger.info(f"FINAL STEP: Creating recommendation for {campus.name}")

        # Initialize and populate the notes list for this recommendation
        notes = [
            f"Campus passed exclusion checks.",
            f"Bed type: {closest_campus_data.get('bed_type', 'N/A')}, {closest_campus_data.get('beds_available', 'N/A')} available.",
            f"Transport mode: {closest_campus_data.get('transport_mode', 'N/A')}, travel time: {closest_campus_data.get('travel_time_minutes', 0.0):.1f} minutes.",
            f"Selected as closest eligible campus with available beds."
        ]

        # Prepare data for LLM explanation
        current_bed_availability = BedAvailability(
            campus_id=campus.campus_id if campus.campus_id else "unknown",
            bed_type=closest_campus_data['bed_type'],
            available_beds=closest_campus_data['beds_available'],
            last_updated="N/A"  # Placeholder, ideally from actual data source
        )

        current_transport_option = TransportOption(
            mode=closest_campus_data['transport_mode'],
            estimated_time_minutes=closest_campus_data['travel_time_minutes'],
            viable=True  # Assumed viable if it's the best option
        )

        # Attempt to generate LLM-based explanation details
        # Placeholder for actual exclusion reasons if needed by LLM prompt
        # For now, passing None or an empty list for exclusion_reasons_for_llm
        exclusion_reasons_for_llm = [] # Or None
        # The 'notes' list collected earlier can be used for 'other_notes'

        llm_reasoning_details = generate_llm_explanation(
            transfer_request=request,
            recommended_campus=campus,
            bed_availability=current_bed_availability,
            best_transport_option=current_transport_option,
            all_scoring_results=request.processed_scoring_results if request.processed_scoring_results else [],
            exclusion_reasons=exclusion_reasons_for_llm, # Pass compiled exclusion reasons if available
            other_notes=notes # Pass the 'notes' list collected during the process
        )

        # Create recommendation object
        final_recommendation = Recommendation(
            transfer_request_id=request.request_id,
            recommended_campus_id=campus.campus_id,
            reason=f"Campus {campus.name} selected: passed exclusion checks, has {closest_campus_data['beds_available']} {closest_campus_data['bed_type']} beds available, and is the closest eligible campus at {closest_campus_data['travel_time_minutes']:.1f} minutes by {closest_campus_data['transport_mode']}.",
            confidence_score=100.0, # Placeholder, can be refined
            explainability_details=llm_reasoning_details, # Use LLM generated details
            notes=notes, # Overall notes for the recommendation
            scoring_results=request.processed_scoring_results, # ADDED
        )

        # Set the final travel time and mode on the recommendation object
        final_recommendation.final_travel_time_minutes = closest_campus_data.get("travel_time_minutes")
        final_recommendation.chosen_transport_mode = closest_campus_data.get("transport_mode")

        # Populate simple_explanation using the newly created final_recommendation and patient_data from the request
        final_recommendation.simple_explanation = generate_simple_explanation(
            recommendation=final_recommendation, 
            patient_data=request.patient_data
        )

        print("RECOMMENDATION CREATED SUCCESSFULLY!")
        print(
            f"Recommended: {campus.name} via {closest_campus_data['transport_mode']}"
        )
        sys.stdout.flush()
        return final_recommendation

    except Exception as e:
        print(f"!!! CRITICAL ERROR IN RECOMMENDATION ENGINE: {e} !!!")
        traceback.print_exc()
        sys.stdout.flush()
        return None

    """
    Recommends a hospital campus for patient transfer using a simple algorithm:
    1. Check for campus exclusions
    2. Check for bed status
    3. Find the closest campus

    Args:
        request: The transfer request containing patient data and origin.
        campuses: List of available hospital campuses.
        current_weather: Current weather conditions affecting transport.
        available_transport_modes: Available modes of transport.
        transport_time_estimates: Pre-calculated transport time estimates (optional).
        human_suggestions: Human expert input on care level (optional).

    Returns:
        A Recommendation object with the best hospital choice, or None if no suitable hospital found.
    """
    # Guard clause: if no campuses, return None
    if not campuses:
        print(f"DEBUG: No campuses available for request {request.request_id}.")
        return None

    print(f"DEBUG: Starting recommendation process with {len(campuses)} campuses")

    # Get care level suggestions if available
    care_levels = []
    human_suggestions_data = request.transport_info.get("human_suggestions", {})
    if human_suggestions_data and "care_levels" in human_suggestions_data:
        care_levels = human_suggestions_data["care_levels"]
        print(f"DEBUG: Found care level suggestions: {care_levels}")
    else:
        print(f"DEBUG: No care level suggestions found in {human_suggestions_data}")

    # Set up origin location for travel calculations
    sending_facility = request.sending_facility_location
    print(f"DEBUG: Origin location: {sending_facility}")

    # STEP 1: Check exclusions for each campus
    eligible_campuses = []

    for campus in campuses:
        exclusions = check_exclusions(request.patient_data, campus)
        if not exclusions:
            eligible_campuses.append(campus)
        else:
            exclusion_names = [e.name for e in exclusions]
            print(f"Campus {campus.name} excluded due to: {exclusion_names}")

    if not eligible_campuses:
        print(f"DEBUG: No eligible campuses found after exclusion checks.")
        return None

    print(
        f"DEBUG: Found {len(eligible_campuses)} campuses that passed exclusion checks"
    )

    # STEP 2: Check bed status for eligible campuses
    campuses_with_beds = []

    print(f"DEBUG: Checking bed status for {len(eligible_campuses)} eligible campuses")

    for campus in eligible_campuses:
        print(f"DEBUG: Checking beds for campus {campus.name}")
        # Check ICU/PICU beds if needed
        if "ICU" in care_levels or "PICU" in care_levels:
            if campus.bed_census.icu_beds_available > 0:
                campuses_with_beds.append(
                    {
                        "campus": campus,
                        "bed_type": "ICU/PICU",
                        "beds_available": campus.bed_census.icu_beds_available,
                    }
                )
        # Check NICU beds if needed
        elif "NICU" in care_levels:
            if campus.bed_census.nicu_beds_available > 0:
                campuses_with_beds.append(
                    {
                        "campus": campus,
                        "bed_type": "NICU",
                        "beds_available": campus.bed_census.nicu_beds_available,
                    }
                )
        # Default to general beds
        else:
            if campus.bed_census.available_beds > 0:
                campuses_with_beds.append(
                    {
                        "campus": campus,
                        "bed_type": "General",
                        "beds_available": campus.bed_census.available_beds,
                    }
                )

    if not campuses_with_beds:
        print(f"DEBUG: No campuses with available beds found.")
        return None

    print(f"DEBUG: Found {len(campuses_with_beds)} campuses with available beds")

    # STEP 3: Calculate travel times and find closest campus
    campuses_with_distance = []

    for campus_data in campuses_with_beds:
        campus = campus_data["campus"]
        travel_times = {}

        # Ground travel
        if TransportMode.GROUND_AMBULANCE in available_transport_modes:
            try:
                print(f"DEBUG: Calculating ground travel time to {campus.name}")
                campus_obj = campus["campus"] if isinstance(campus, dict) else campus
                road_info = get_road_travel_info(sending_facility, campus_obj.location)
                print(f"DEBUG: Ground travel info: {road_info}")
                if road_info and "duration_minutes" in road_info:
                    travel_times[TransportMode.GROUND_AMBULANCE] = road_info[
                        "duration_minutes"
                    ]
                    print(
                        f"DEBUG: Ground travel time: {road_info['duration_minutes']} minutes"
                    )
            except Exception as e:
                print(f"ERROR: Error calculating road travel to {campus.name}: {e}")

        # Air travel
        if TransportMode.AIR_AMBULANCE in available_transport_modes:
            try:
                print(f"DEBUG: Calculating air travel time to {campus.name}")
                # Ensure we're getting the campus object correctly, whether it's directly a campus or inside a dict
                campus_obj = campus_data["campus"]
                air_info = get_air_travel_info(
                    sending_facility, campus_obj.location, weather_data
                )
                print(f"DEBUG: Air travel info: {air_info}")
                if air_info and "duration_minutes" in air_info:
                    travel_times[TransportMode.AIR_AMBULANCE] = air_info[
                        "duration_minutes"
                    ]
                    print(
                        f"DEBUG: Air travel time: {air_info['duration_minutes']} minutes"
                    )
            except Exception as e:
                print(f"ERROR: Error calculating air travel to {campus.name}: {e}")

        # Skip if no valid travel options
        if not travel_times:
            print(f"No valid travel options for {campus.name}")
            continue

        # Find fastest mode
        fastest_mode = min(travel_times.items(), key=lambda x: x[1])

        # Add to campuses with distance
        campuses_with_distance.append(
            {
                "campus": campus,
                "bed_type": campus_data["bed_type"],
                "beds_available": campus_data["beds_available"],
                "transport_mode": fastest_mode[0],
                "travel_time_minutes": fastest_mode[1],
            }
        )

    # If no campuses with valid travel options, return None
    if not campuses_with_distance:
        print(f"DEBUG: No campuses with valid travel routes found.")
        return None

    print(
        f"DEBUG: Found {len(campuses_with_distance)} campuses with valid travel routes"
    )

    # Sort by travel time (closest first)
    campuses_with_distance.sort(key=lambda x: x["travel_time_minutes"])
    print(
        f"DEBUG: Sorted campuses by travel time: {[(c['campus'].name, c['travel_time_minutes']) for c in campuses_with_distance]}"
    )

    # Select the closest campus
    if campuses_with_distance:
        best_option = campuses_with_distance[0]
        chosen_campus = best_option["campus"]
        print(
            f"DEBUG: Selected best campus: {chosen_campus.name} with travel time {best_option['travel_time_minutes']} minutes"
        )
    else:
        print(
            "DEBUG: CRITICAL ERROR - No campuses with distance available despite earlier check"
        )
        return None

    # Prepare explanation notes
    notes = [
        f"Campus passed exclusion checks",
        f"Bed type: {best_option['bed_type']}, {best_option['beds_available']} available",
        f"Transport mode: {best_option['transport_mode']}, travel time: {best_option['travel_time_minutes']:.1f} minutes",
        f"Selected as closest eligible campus with available beds",
    ]

    try:
        # Construct Pydantic models for bed availability and transport option
        current_bed_availability = BedAvailability(
            campus_id=best_option["campus"].campus_id,
            bed_type=best_option["bed_type"],
            available_beds=best_option["beds_available"],
            last_updated="N/A" # Assuming not immediately available here, or fetch if possible
        )
        current_transport_option = TransportOption(
            mode=TransportMode(best_option["transport_mode"]), # Ensure this is a valid TransportMode enum
            estimated_time_minutes=best_option["travel_time_minutes"],
            cost=0 # Assuming cost is not a factor here or not available
        )

        # If an LLM explainer is configured and available, use it
        # This now expects more detailed inputs for a richer prompt
        explainability_details = generate_llm_explanation(
            transfer_request=request, # Full TransferRequest object
            recommended_campus=best_option["campus"], # Campus object
            bed_availability=current_bed_availability, # BedAvailability Pydantic model
            best_transport_option=current_transport_option, # TransportOption Pydantic model
            all_scoring_results=request.processed_scoring_results, # Pass the list of ScoringResult objects
            exclusion_reasons=None, # Optional: reasons other campuses were excluded if relevant here
            other_notes=notes # General notes from the decision process
        )
        logger.info(f"LLM explanation generated for {best_option['campus'].name}")
    except Exception as e:
        logger.error(f"Failed to generate LLM explanation: {e}. Falling back to predefined reasoning.")
        # Use the fallback from explainer.py directly if LLM fails
        explainability_details = FALLBACK_REASONING # CORRECTED to use imported constant
        logger.info(f"DEBUG: Using fallback LLMReasoningDetails: {explainability_details}")

    # Create final recommendation
    try:
        print(f"DEBUG: Creating recommendation object")
        final_recommendation = Recommendation(
            transfer_request_id=request.request_id,
            recommended_campus_id=best_option["campus"].campus_id,
            recommended_campus_name=best_option["campus"].name,
            reason=f"Campus {best_option['campus'].name} selected: passed exclusion checks, has {best_option['beds_available']} {best_option['bed_type']} beds available, and is the closest eligible campus at {best_option['travel_time_minutes']:.1f} minutes by {best_option['transport_mode']}.",
            confidence_score=100.0,  # Simple algorithm is deterministic
            explainability_details=explainability_details,  # Use the new LLM-generated details
            notes=notes,
            scoring_results=request.processed_scoring_results, # ADDED
            transport_details={
                "mode": str(best_option['transport_mode']),
                "estimated_time_minutes": best_option['travel_time_minutes'],
                "special_requirements": "None"
            },
            conditions={
                "weather": "Clear",
                "traffic": "Normal traffic conditions"
            }
        )
        print(f"DEBUG: Successfully created recommendation: {final_recommendation}")
        print(f"DEBUG: Transport details: {final_recommendation.transport_details}")
        print(f"DEBUG: Transport mode: {final_recommendation.transport_details.get('mode', 'Not in dict')}")
        print(f"DEBUG: Estimated time: {final_recommendation.transport_details.get('estimated_time_minutes', 'Not in dict')} minutes")
        print(
            f"Recommendation: {best_option['campus'].name}. Travel: {best_option['travel_time_minutes']:.1f} min via {best_option['transport_mode']}."
        )
        # Populate simple_explanation using the newly created final_recommendation and patient_data from the request
        final_recommendation.simple_explanation = generate_simple_explanation(
            recommendation=final_recommendation, 
            patient_data=request.patient_data
        )
        return final_recommendation
    except Exception as e:
        print(f"ERROR: Failed to create recommendation: {e}")
        print(f"DEBUG: Request ID: {request.request_id}")
        print(f"DEBUG: Campus ID: {best_option['campus'].campus_id}")
        print(f"DEBUG: Notes: {notes}")
        return None

# Helper function to find the best transport option (example)
