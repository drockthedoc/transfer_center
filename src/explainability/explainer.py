"""
Generates simplified explanations for transfer recommendations.

This module provides a basic approach to explainability, summarizing key factors
that led to a specific hospital campus recommendation. It's designed to be
extended with more sophisticated methods (e.g., SHAP) in the future.
"""
from typing import Dict, List
# from src.core.models import HospitalCampus, PatientData, Recommendation # Avoid circular if Recommendation uses this

def generate_simple_explanation(
    chosen_campus_name: str,
    decision_details: Dict, # This will be best_option from decision_engine
    llm_conditions: List[str]
) -> Dict[str, any]:
    """
    Generates a simplified, human-readable explanation for a recommendation.

    Args:
        chosen_campus_name: The name of the recommended hospital campus.
        decision_details: A dictionary containing details from the decision engine's
                          evaluation of the chosen campus (e.g., score, travel time,
                          chosen transport mode, notes). This typically corresponds to
                          the 'best_option' dictionary in `recommend_campus`.
        llm_conditions: A list of potential patient conditions identified by the
                        LLM text parsing.

    Returns:
        A dictionary structured to provide a basic explanation, including:
            - "recommended_campus_name": Name of the chosen campus.
            - "key_factors_for_recommendation": List of primary reasons (score, travel).
            - "llm_identified_patient_conditions": Conditions from LLM.
            - "other_considerations_from_notes": Full log of notes from the
                                                 decision process for the chosen campus.
    """
    explanation = {
        "recommended_campus_name": chosen_campus_name,
        "key_factors_for_recommendation": [],
        "llm_identified_patient_conditions": llm_conditions,
        "other_considerations_from_notes": decision_details.get("notes", []) 
    }
    
    # Ensure score is formatted correctly if it's a float
    score = decision_details.get('score', 'N/A')
    if isinstance(score, float):
        score_str = f"{score:.2f}"
    else:
        score_str = str(score) # Keep as N/A or other string if not float
        
    explanation["key_factors_for_recommendation"].append(f"Score: {score_str}")
    
    explanation["key_factors_for_recommendation"].append(
        f"Estimated Travel: {decision_details.get('final_travel_time_minutes', 'N/A')} min "
        f"via {decision_details.get('chosen_transport_mode', 'N/A')}."
    )
    # Add bed info from notes if possible (this requires parsing notes or more structured data)
    # For now, the raw notes are in 'other_considerations_from_notes'
    return explanation
