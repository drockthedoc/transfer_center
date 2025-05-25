"""
Generates simplified explanations for transfer recommendations.

This module provides a basic approach to explainability, summarizing key factors
that led to a specific hospital campus recommendation. It's designed to be
extended with more sophisticated methods (e.g., SHAP) in the future.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from rich import print as rprint

# Configure logger for this module
logger = logging.getLogger(__name__) # Use the module's name for the logger
logger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all levels of logs

# Add a stream handler if no handlers are configured, to ensure output to console
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    # Basic formatter, customize as needed
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    logger.propagate = False # Prevent duplicate logs if root logger also has a handler

# Ensure all model types are imported and available
from src.core.models import (
    BedAvailability, HospitalCampus, PatientData, Recommendation, ScoringResult, 
    TransportOption, LLMReasoningDetails, TransferRequest
)
from src.llm.llm_client import get_llm_client, LLMClient

# Fallback message if LLM fails or parsing is unsuccessful
FALLBACK_REASONING = LLMReasoningDetails(
    main_recommendation_reason="LLM explanation could not be generated or parsed.",
    alternative_reasons={},
    key_factors_considered=["Error in LLM processing"],
    confidence_explanation="Confidence impacted by LLM failure."
)

def generate_simple_explanation(
    recommendation: Recommendation, 
    patient_data: PatientData
) -> Dict[str, Any]:
    """
    Generates a simplified, human-readable explanation for a recommendation.

    Args:
        recommendation: The recommendation object containing details of the chosen campus.
        patient_data: A dictionary containing details about the patient.

    Returns:
        A dictionary structured to provide a basic explanation, including:
            - "recommended_campus_name": Name of the chosen campus.
            - "key_factors_for_recommendation": List of primary reasons (score, travel).
            - "llm_identified_patient_conditions": Conditions from LLM.
            - "other_considerations_from_notes": Full log of notes from the
                                                 decision process for the chosen campus.
    """
    explanation = {
        "recommended_campus_name": recommendation.recommended_campus_name,
        "key_factors_for_recommendation": [
            f"Patient Care Level: {patient_data.care_level}", 
            f"Estimated Travel: {recommendation.final_travel_time_minutes:.2f} min via {recommendation.chosen_transport_mode}."
        ],
        "llm_identified_patient_conditions": [], 
        "other_considerations_from_notes": recommendation.notes or []
    }
    return explanation


def generate_llm_explanation(
    transfer_request: TransferRequest, 
    recommended_campus: HospitalCampus,
    bed_availability: BedAvailability,
    best_transport_option: TransportOption,
    all_scoring_results: List[ScoringResult],
    exclusion_reasons: Optional[List[str]] = None,
    other_notes: Optional[List[str]] = None
) -> LLMReasoningDetails:
    """
    Generates a detailed explanation for a transfer recommendation using an LLM.
    Constructs a prompt, calls the LLM, and parses the JSON response into LLMReasoningDetails.
    """
    logger.debug(f"--- Entered generate_llm_explanation for campus: {recommended_campus.name} ---")
    logger.info(f"Generating LLM explanation for campus: {recommended_campus.name}")

    # Access patient data
    extracted_data = transfer_request.patient_data.extracted_data
    rprint(f"DEBUG EXPLAINER: generate_llm_explanation working with extracted_data: {extracted_data}") # ADDED

    # Safely access patient details from extracted_data with fallbacks
    # The keys like 'age_years', 'sex', 'primary_diagnosis', 'raw_text_summary' 
    # should now be populated by the updated llm.classification.parse_patient_text
    patient_age = extracted_data.get(
        "age_years"
    ) or extracted_data.get("age", "N/A")
    
    patient_sex = extracted_data.get("sex", "N/A")
    primary_diagnosis = extracted_data.get("primary_diagnosis", "N/A")
    clinical_notes_summary = extracted_data.get("raw_text_summary", "")

    rprint(f"DEBUG EXPLAINER: Values used for prompt parts: age='{patient_age}', sex='{patient_sex}', diagnosis='{primary_diagnosis}'") # ADDED

    # Construct patient summary for the prompt
    patient_summary = f"Patient Age: {patient_age} years. Sex: {patient_sex}. Primary Diagnosis: {primary_diagnosis}. "
    if clinical_notes_summary:
        patient_summary += f"Clinical Notes: {clinical_notes_summary[:500]}... " # Truncate for brevity

    scoring_summary = "Key Scoring Results:\n"
    if all_scoring_results:
        for score_res in all_scoring_results[:3]: # Show top 3 scores
            scoring_summary += f"- {score_res.score_name}: {score_res.score_value} (Interpretation: {score_res.interpretation})\n"
    else:
        scoring_summary += "- No specific scoring systems applied or results available.\n"

    recommendation_context = f"Recommended Campus: {recommended_campus.name} (ID: {recommended_campus.campus_id}). "
    recommendation_context += f"Bed Availability: {bed_availability.bed_type} with {bed_availability.available_beds} beds. "
    recommendation_context += f"Transport: {best_transport_option.mode} in {best_transport_option.estimated_time_minutes:.1f} minutes. " 
    if exclusion_reasons:
        recommendation_context += f"Reasons for excluding other campuses: {'; '.join(exclusion_reasons)}. "
    if other_notes:
        recommendation_context += f"Other decision notes: {'; '.join(other_notes)}. "

    prompt = f"""
        You are an AI assistant helping explain pediatric hospital transfer recommendations.
        Based on the following information, provide a structured JSON explanation for why a specific hospital campus is recommended.

        Patient Summary:
        {patient_summary}

        {scoring_summary}

        Recommendation Context:
        {recommendation_context}

        Please generate a JSON object with the following keys:
        - "main_recommendation_reason": A concise primary reason for choosing this campus (e.g., "Closest specialized PICU bed with appropriate transport.").
        - "alternative_reasons": An object where keys are other considered (but not chosen) campus IDs (if any were seriously considered and rejected for specific reasons relevant here) and values are brief reasons for not choosing them.
        - "key_factors_considered": A list of strings detailing the most critical factors (e.g., "Patient requires PICU level care", "Proximity and rapid transport essential", "Specific service X available at recommended campus").
        - "confidence_explanation": A brief explanation of the confidence in this recommendation (e.g., "High confidence due to clear-cut best option based on needs and availability.").

        Example JSON output format:
        {{ "main_recommendation_reason": "string", "alternative_reasons": {{ "campus_id_1": "reason_string" }}, "key_factors_considered": ["string1", "string2"], "confidence_explanation": "string" }}

        Ensure the output is ONLY the JSON object, with no other text before or after it.
        JSON Response:
    """

    logger.debug(f"Constructed LLM Prompt:\n{prompt}")

    try:
        llm_client: LLMClient = get_llm_client() # Uses env var LLM_PROVIDER or defaults to 'openai'
        logger.info(f"LLM client obtained for provider: {llm_client.provider_name}")
        
        raw_llm_response = llm_client.generate(prompt, max_tokens=1000, temperature=0.2)
        logger.info(f"Raw LLM response received (first 100 chars): {raw_llm_response[:100]}")

        # Attempt to parse the JSON response
        # The LLM should return *only* JSON. If it's wrapped in markdown, try to extract.
        if raw_llm_response.strip().startswith("```json"):
            json_str = raw_llm_response.strip().split("```json\n", 1)[1].split("\n```", 1)[0]
        elif raw_llm_response.strip().startswith("{") and raw_llm_response.strip().endswith("}"):
            json_str = raw_llm_response.strip()
        else:
            logger.warning(f"LLM response does not appear to be well-formed JSON. Attempting direct parse. Response: {raw_llm_response}")
            json_str = raw_llm_response # Hope for the best

        parsed_json = json.loads(json_str)
        
        # Validate and construct LLMReasoningDetails Pydantic model
        reasoning_details = LLMReasoningDetails(
            main_recommendation_reason=parsed_json.get("main_recommendation_reason", "LLM provided no main reason."),
            alternative_reasons=parsed_json.get("alternative_reasons", {}),
            key_factors_considered=parsed_json.get("key_factors_considered", []), 
            confidence_explanation=parsed_json.get("confidence_explanation", "LLM provided no confidence explanation.")
        )
        logger.info("Successfully parsed LLM response into LLMReasoningDetails.")
        return reasoning_details

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}. Raw response: {raw_llm_response}")
        return FALLBACK_REASONING
    except ConnectionError as e:
        logger.error(f"LLM client connection error: {e}")
        return FALLBACK_REASONING
    except RuntimeError as e: # Catch errors from get_llm_client (e.g. config issues)
        logger.error(f"LLM client initialization error: {e}")
        return FALLBACK_REASONING
    except Exception as e:
        logger.exception(f"An unexpected error occurred during LLM explanation generation: {e}")
        return FALLBACK_REASONING
