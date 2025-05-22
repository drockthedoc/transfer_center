from typing import List, Optional, Dict
from src.core.models import TransferRequest, HospitalCampus, WeatherData, TransportMode, Recommendation, PatientData, BedCensus
from src.core.exclusion_checker import check_exclusions
# from src.utils.geolocation import calculate_distance # No longer directly used for scoring, only by travel_calculator
from src.utils.travel_calculator import get_road_travel_info, get_air_travel_info
from src.llm.classification import parse_patient_text # Now imported
from src.explainability.explainer import generate_simple_explanation # NEW IMPORT

# ADVERSE_WEATHER_FOR_AIR constant can be removed, as this logic is now in get_air_travel_info

def recommend_campus(
    request: TransferRequest,
    campuses: List[HospitalCampus],
    current_weather: WeatherData,
    available_transport_modes: List[TransportMode] 
) -> Optional[Recommendation]:
    """
    Recommends a hospital campus for patient transfer based on a comprehensive evaluation.

    The function processes a transfer request by:
    1.  Parsing patient data using a simulated LLM to identify potential clinical conditions.
    2.  Iterating through available hospital campuses. For each campus, it:
        a. Checks against campus-specific exclusion criteria.
        b. Assesses bed availability (general, ICU, NICU) based on LLM-derived patient needs.
        c. Calculates travel time and viability for both ground and air transport,
           considering current weather conditions for air travel.
        d. Selects the optimal transport mode (ground or air).
        e. Calculates a composite score based on bed availability and travel time.
    3.  Filters out unsuitable campuses (due to exclusions, lack of required beds, or
        unavailability of transport).
    4.  Sorts remaining eligible campuses by their composite score in descending order.
    5.  Selects the top-scoring campus as the recommendation.
    6.  Generates an explanation for the recommendation.

    Args:
        request: The TransferRequest object containing patient data and sending facility details.
        campuses: A list of HospitalCampus objects representing available destination campuses.
        current_weather: A WeatherData object representing the current weather conditions.
        available_transport_modes: A list of TransportMode enums indicating which modes
                                   (e.g., ground, air) are generally available.

    Returns:
        An Optional[Recommendation] object. If a suitable campus is found, it contains
        details of the recommended campus, the reason for recommendation, confidence score,
        and explainability notes. Returns None if no suitable campus is identified.
    """
    eligible_campuses_with_scores: List[Dict] = [] 

    # --- LLM Parsing (Early in the function) ---
    llm_output = parse_patient_text(request.patient_data.chief_complaint + " " + request.patient_data.clinical_history)
    potential_conditions = llm_output.get("potential_conditions", [])
    # extracted_vitals = llm_output.get("extracted_vital_signs", {}) # For future use
    # Note: Adding general LLM notes to overall request context might be better if done once.
    # However, if it influences per-campus decisions, it can be added to notes_for_this_campus too.

    for campus in campuses:
        notes_for_this_campus: List[str] = []
        # Add LLM identified conditions to each campus's notes for context during decision making for that campus.
        notes_for_this_campus.append(f"LLM identified potential conditions: {potential_conditions}.")
        
        # 1. Check Exclusions
        met_exclusions = check_exclusions(request.patient_data, campus)
        if met_exclusions:
            exclusion_reasons = ", ".join([ex.criteria_name for ex in met_exclusions])
            notes_for_this_campus.append(f"Excluded due to: {exclusion_reasons}.")
            print(f"Campus {campus.name} excluded for request {request.request_id} due to: {exclusion_reasons}")
            continue 
        notes_for_this_campus.append("Passed exclusion criteria.")

        # 2. Refined Bed Availability Check
        # This mapping should ideally be more comprehensive and potentially configurable
        CONDITION_TO_BED_TYPE_MAP = { # Defined here as per prompt, consider global if shared
            "cardiac": "icu", 
            "neurological": "icu", 
            "trauma": "icu", # Severe trauma
            "sepsis": "icu",
            "respiratory_distress": "icu", # If LLM can identify this specifically
            "pediatric_emergency": "nicu", 
            # "burn_severe": "burn_unit" # Example for future expansion
        }

        required_specialty_bed_type = None # Will be "ICU", "NICU", or None (meaning general)
        patient_needs_icu = False
        patient_needs_nicu = False

        # Determine specialty bed needs from LLM's potential conditions
        if any(cond in ["cardiac", "neurological", "trauma", "sepsis", "respiratory_distress"] for cond in potential_conditions):
            patient_needs_icu = True
            required_specialty_bed_type = "ICU"
        
        # Check for pediatric emergency, which might imply NICU or PICU (handled by ICU check here)
        if "pediatric_emergency" in potential_conditions:
            patient_needs_nicu = True # Mark as needing NICU specific check
            if patient_needs_icu: # Patient is pediatric AND needs ICU -> PICU (conceptually)
                notes_for_this_campus.append("Patient identified as pediatric needing ICU (PICU). ICU check will proceed.")
                # required_specialty_bed_type is already "ICU", which is fine.
            else: # Pediatric, but no other overt ICU indicators from the list, so NICU is primary.
                required_specialty_bed_type = "NICU"
        
        bed_check_passed = False
        if patient_needs_icu: # This covers general ICU and PICU needs
            if campus.bed_census.icu_beds_available > 0:
                notes_for_this_campus.append(f"ICU beds available: {campus.bed_census.icu_beds_available}.")
                bed_check_passed = True
            else:
                notes_for_this_campus.append("No ICU beds available.")
        elif patient_needs_nicu: # Only checked if NOT primarily needing ICU (e.g. pediatric_emergency without other critical flags)
            if campus.bed_census.nicu_beds_available > 0:
                notes_for_this_campus.append(f"NICU beds available: {campus.bed_census.nicu_beds_available}.")
                bed_check_passed = True
            else:
                notes_for_this_campus.append("No NICU beds available.")
        else: # No specific ICU/NICU need identified from potential_conditions, check general beds
            if campus.bed_census.available_beds > 0:
                notes_for_this_campus.append(f"General beds available: {campus.bed_census.available_beds}.")
                bed_check_passed = True
            else:
                notes_for_this_campus.append("No general beds available.")

        if not bed_check_passed:
            # Construct a more informative message for the print log
            needed_bed_log_msg = required_specialty_bed_type if required_specialty_bed_type else "General"
            print(f"Campus {campus.name} unsuitable for {request.request_id} due to bed availability (Needed: {needed_bed_log_msg}). Notes: {' '.join(notes_for_this_campus)}")
            continue # Skip to next campus if bed requirements not met
        
        # If we reach here, bed_check_passed is True.
        # The bed_score in the scoring section will use this implicit pass.

        # 3. Advanced Transport Calculations & Mode Selection
        road_travel_info = get_road_travel_info(request.sending_facility_location, campus.location)
        road_time_minutes = road_travel_info.get("time_minutes", float('inf'))
        road_distance_km = road_travel_info.get("distance_km", float('inf')) # road distance
        notes_for_this_campus.append(f"Ground: {road_time_minutes if road_time_minutes != float('inf') else 'N/A'} min ({road_distance_km if road_distance_km != float('inf') else 'N/A'} km) via {road_travel_info.get('source', 'N/A')}.")

        air_travel_viable = False
        air_time_minutes = float('inf')
        # air_distance_km = float('inf') # Direct line distance for air, if needed for notes

        if TransportMode.AIR_AMBULANCE in available_transport_modes and campus.helipads:
            # Simplification: use the first helipad. Real system might evaluate all or nearest.
            destination_helipad_location = campus.helipads[0].location 
            air_travel_info = get_air_travel_info(
                request.sending_facility_location, 
                destination_helipad_location, 
                current_weather
            )
            air_travel_viable = air_travel_info.get("viable", False)
            if air_travel_viable:
                air_time_minutes = air_travel_info.get("time_minutes", float('inf'))
                air_distance_km_flight = air_travel_info.get("distance_km", float('inf')) # This is flight distance
                notes_for_this_campus.append(f"Air: {air_time_minutes if air_time_minutes != float('inf') else 'N/A'} min ({air_distance_km_flight if air_distance_km_flight != float('inf') else 'N/A'} km flight) - {air_travel_info.get('reason', '')}.")
            else:
                notes_for_this_campus.append(f"Air: Not viable - {air_travel_info.get('reason', 'No details')}.")
        else:
            if TransportMode.AIR_AMBULANCE not in available_transport_modes:
                 notes_for_this_campus.append("Air: Air ambulance not in available transport modes.")
            if not campus.helipads:
                 notes_for_this_campus.append("Air: No helipad on campus.")


        chosen_transport_mode = "Ground"
        final_travel_time_minutes = road_time_minutes
        # final_travel_distance_km = road_distance_km # Used for notes, not scoring

        if air_travel_viable and air_time_minutes < road_time_minutes:
            chosen_transport_mode = "Air"
            final_travel_time_minutes = air_time_minutes
            # final_travel_distance_km = air_distance_km_flight # If needed for notes

        notes_for_this_campus.append(f"Chosen Transport: {chosen_transport_mode} (Est. Time: {final_travel_time_minutes if final_travel_time_minutes != float('inf') else 'N/A'} min).")
        
        if final_travel_time_minutes == float('inf'):
            notes_for_this_campus.append("Transport time calculation failed or chosen mode unavailable.")
            print(f"Campus {campus.name} unsuitable due to transport issues for request {request.request_id}. Notes: {' '.join(notes_for_this_campus)}")
            continue # Cannot reach this campus

        # 4. Calculate Score (Updated for Travel Time)
        score = 0.0
        bed_score_weight = 0.5 
        time_score_weight = 0.5 

        bed_score = 100.0 if campus.bed_census.available_beds > 0 else 0.0 # Max score for beds
        score += bed_score_weight * bed_score
        
        max_travel_time_heuristic_minutes = 180.0 # e.g., 3 hours
        # Normalize time: (max_time - actual_time) / max_time
        # If actual_time > max_time, score is 0 or negative. Clamp at 0.
        normalized_time_score = max(0, (max_travel_time_heuristic_minutes - final_travel_time_minutes) / max_travel_time_heuristic_minutes) * 100
        score += time_score_weight * normalized_time_score
        score = max(0, score) # Ensure score is not negative

        eligible_campuses_with_scores.append({
            "campus": campus,
            "score": score,
            "final_travel_time_minutes": final_travel_time_minutes,
            "chosen_transport_mode": chosen_transport_mode,
            "notes": notes_for_this_campus # Contains detailed breakdown
        })
        print(f"Campus {campus.name} considered for {request.request_id}. Score: {score:.2f}, Time: {final_travel_time_minutes} min via {chosen_transport_mode}.")

    if not eligible_campuses_with_scores:
        print(f"No suitable campus found for request {request.request_id}.")
        return None

    eligible_campuses_with_scores.sort(key=lambda x: x["score"], reverse=True)
    best_option = eligible_campuses_with_scores[0]
    chosen_campus = best_option["campus"]
    
    reason_parts = [
        f"Top choice: {chosen_campus.name}.",
        f"Score: {best_option['score']:.2f}.",
        f"Est. Travel: {best_option['final_travel_time_minutes']:.0f} min via {best_option['chosen_transport_mode']}.",
        f"Beds: {chosen_campus.bed_census.available_beds} available."
    ]
    # Add other key notes from best_option['notes'] if needed for the main reason.
    # For example, if exclusions were passed, or specific bed types were key, that could be added.

    simple_expl_details = generate_simple_explanation(
       chosen_campus_name=chosen_campus.name,
       decision_details=best_option, # best_option contains notes, score, time, mode
       llm_conditions=llm_output.get("potential_conditions", [])
    )

    recommendation = Recommendation(
        transfer_request_id=request.request_id,
        recommended_campus_id=chosen_campus.campus_id,
        reason=" ".join(reason_parts),
        confidence_score=best_option["score"],
        explainability_details=simple_expl_details, # Populate with the simpler explanation
        notes=best_option["notes"] 
    )
    print(f"Recommendation for {request.request_id}: {chosen_campus.name}. Reason: {recommendation.reason}. Explanation: {simple_expl_details}")
    return recommendation
