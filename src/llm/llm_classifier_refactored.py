"""
LLM classifier integration for the Transfer Center GUI.

This module handles the integration with local LLM services through LM Studio's
OpenAI-compatible API for text classification and information extraction.
"""

import json
import logging
import re
import traceback
from typing import Any, Dict, List, Optional

import openai

from src.llm.components.entity_extraction import EntityExtractor
from src.llm.components.exclusion_evaluation import ExclusionEvaluator
from src.llm.components.recommendation import RecommendationGenerator
from src.llm.components.specialty_assessment import SpecialtyAssessor

# Set up logging
logger = logging.getLogger(__name__)


class LLMClassifier:
    """
    Handles interaction with LLMs for text classification through LM Studio.

    This class provides methods to process clinical text, extract relevant information,
    and classify patients based on their needs. It uses LM Studio's local API which
    is compatible with the OpenAI API format.
    """

    def __init__(self, api_url: str = "http://localhost:1234/v1", model: str = None):
        """
        Initialize the LLM classifier.

        Args:
            api_url: URL for the LM Studio API (default: http://localhost:1234/v1)
            model: Name of the model to use (if None, will attempt to get first available model)
        """
        self.api_url = api_url
        self.available_models = []
        self.client = self._setup_client()

        # Try to get available models
        self.refresh_models()

        # Set model (use specified model, first available model, or fallback)
        if model is not None:
            self.model = model
        elif self.available_models:
            self.model = self.available_models[0]
        else:
            self.model = (
                "fallback_model"  # This will likely fail but provides a default
            )

        # Initialize components
        self._init_components()

    def _setup_client(self) -> openai.OpenAI:
        """Set up the OpenAI client with the LM Studio API URL."""
        return openai.OpenAI(
            base_url=self.api_url,
            api_key="not-needed",  # LM Studio doesn't require an API key
        )

    def _init_components(self):
        """Initialize the LLM processing components."""
        self.entity_extractor = EntityExtractor(self.client, self.model)
        self.specialty_assessor = SpecialtyAssessor(self.client, self.model)
        self.exclusion_evaluator = ExclusionEvaluator(self.client, self.model)
        self.recommendation_generator = RecommendationGenerator(self.client, self.model)

    def set_api_url(self, api_url: str):
        """Update the API URL and reinitialize the client."""
        self.api_url = api_url
        self.client = self._setup_client()
        self.refresh_models()
        self._init_components()

    def set_model(self, model: str):
        """Update the model name."""
        self.model = model
        self._init_components()

    def refresh_models(self) -> List[str]:
        """Query the API for available models and update the available_models list."""
        self.available_models = []
        try:
            response = self.client.models.list()
            for model in response.data:
                self.available_models.append(model.id)
            logger.info(
                f"Found {len(self.available_models)} available models: {self.available_models}"
            )
            return self.available_models
        except Exception as e:
            logger.error(f"Error fetching available models: {str(e)}")
            return []

    def test_connection(
        self, api_url: Optional[str] = None, model: Optional[str] = None
    ) -> tuple:
        """
        Test the connection to the LLM API.

        Args:
            api_url: Optional URL to test (if different from current)
            model: Optional model to test (if different from current)

        Returns:
            Tuple of (success_bool, message_str)
        """
        if api_url:
            self.set_api_url(api_url)

        # Refresh available models first
        available_models = self.refresh_models()
        logger.info(f"Available models for testing: {available_models}")

        # If a specific model was provided, use it
        if model:
            self.set_model(model)
            logger.info(f"Using specified model: {model}")
        # Otherwise, if we have available models, use the first one
        elif available_models and not self.model:
            self.set_model(available_models[0])
            logger.info(f"Using first available model: {available_models[0]}")

        # Check if model is set
        if not self.model or self.model == "fallback_model":
            return False, "No valid model selected or available"

        logger.info(f"Testing connection with model: {self.model}")

        # Try a simple test query
        try:
            # Use a simple system-test prompt
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant for a hospital transfer center.",
                    },
                    {
                        "role": "user",
                        "content": "System test: Respond with 'Connection successful' if you can read this.",
                    },
                ],
                max_tokens=20,
                temperature=0,
            )

            # Check response
            response_text = response.choices[0].message.content
            logger.info(f"Test response: {response_text}")

            if "connection successful" in response_text.lower():
                return True, "Connection successful"
            else:
                return (
                    True,
                    f"Connection works but unexpected response: {response_text}",
                )

        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            error_msg = str(e)
            if "connect" in error_msg.lower():
                error_msg = "Cannot connect to LM Studio API. Is it running?"
            elif "not find" in error_msg.lower() or "no model" in error_msg.lower():
                error_msg = f"Model '{self.model}' not found or not loaded in LM Studio"
            return False, error_msg

    def process_text(
        self,
        text: str,
        patient_data: Optional[Dict] = None,
        sending_facility_location: Optional[Dict] = None,
        available_hospitals: Optional[List[Dict]] = None,
        census_data: Optional[Dict] = None,
        human_suggestions: Optional[Dict] = None,
        scoring_results: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Process clinical text to extract structured information using a multi-step prompting approach.

        Args:
            text: The clinical text to process
            patient_data: Optional dictionary of patient demographic and related data.
            sending_facility_location: Optional dictionary with 'latitude' and 'longitude' of sending facility.
            available_hospitals: Optional list of available hospital dictionaries.
            census_data: Optional dictionary of census data.
            human_suggestions: Optional dictionary of human suggestions to consider
            scoring_results: Optional dictionary containing pediatric scoring system results

        Returns:
            Dictionary with structured information including:
            - success: Boolean indicating if processing was successful.
            - extracted_entities: Patient demographics and extracted clinical information.
            - specialty_assessment: Required care level and specialties.
            - exclusion_evaluation: Results of exclusion criteria evaluation.
            - final_recommendation: Recommendation object.
            - llm_error_message: String message if an error occurred, else None.
        """
        try:
            if not self.client or not self.model or self.model == "fallback_model":
                logger.warning("LLM not properly configured, using fallback processing via process_text")
                fallback_data = self._fallback_process_text(text, human_suggestions, scoring_results)
                return {
                    "success": False,
                    "extracted_entities": fallback_data.get("extracted_entities", {}),
                    "specialty_assessment": fallback_data.get("specialty_assessment", {}),
                    "exclusion_evaluation": None,
                    "final_recommendation": None,
                    "llm_error_message": "LLM not configured; fallback processing used."
                }

            logger.info(f"Processing text with model: {self.model}")

            # Step 1: Extract entities from clinical text
            extracted_entities = self.entity_extractor.extract_entities(text)
            logger.info("Entity extraction complete")

            # Merge patient_data into extracted_entities if provided and not already handled by extractor
            if patient_data:
                extracted_entities.update(patient_data)
                logger.info("Merged patient_data into extracted_entities")

            # Add sending facility location to extracted_entities if provided
            if sending_facility_location:
                extracted_entities['sending_facility_location'] = sending_facility_location
                logger.info(f"Added sending_facility_location to extracted_entities: {sending_facility_location}")
            else:
                logger.warning("sending_facility_location not provided to process_text.")

            # Step 2: Assess specialty needs
            specialty_assessment = self.specialty_assessor.assess_specialties(
                extracted_entities, scoring_results
            )
            logger.info("Specialty assessment complete")

            # Include scoring results in the specialty_assessment if provided (already done by assessor? check)
            if scoring_results:
                specialty_assessment["scoring_results"] = scoring_results

            # Step 3: Evaluate exclusion criteria
            exclusion_evaluation = self.exclusion_evaluator.evaluate_exclusions(
                extracted_entities, specialty_assessment
            )
            logger.info("Exclusion criteria evaluation complete")

            # Step 4: Generate final recommendation
            if not available_hospitals:
                logger.warning("No available_hospitals provided for recommendation generation.")
            
            final_recommendation_obj = (
                self.recommendation_generator.generate_recommendation(
                    extracted_entities=extracted_entities, 
                    specialty_assessment=specialty_assessment,
                    exclusion_evaluation=exclusion_evaluation,
                    available_hospitals=available_hospitals if available_hospitals else [],
                    census_data=census_data
                )
            )
            
            if final_recommendation_obj:
                logger.info(
                    f"Final recommendation generated: {final_recommendation_obj.recommended_campus_id} with confidence {final_recommendation_obj.confidence_score}%"
                )
                return {
                    "success": True,
                    "extracted_entities": extracted_entities,
                    "specialty_assessment": specialty_assessment,
                    "exclusion_evaluation": exclusion_evaluation,
                    "final_recommendation": final_recommendation_obj,
                    "llm_error_message": None
                }
            else:
                logger.error("Recommendation generator returned None.")
                return {
                    "success": False,
                    "extracted_entities": extracted_entities,
                    "specialty_assessment": specialty_assessment,
                    "exclusion_evaluation": exclusion_evaluation,
                    "final_recommendation": None,
                    "llm_error_message": "Recommendation generation failed to produce a result."
                }

        except openai.APIConnectionError as e:
            logger.error(f"LLM API Connection Error in process_text: {str(e)}")
            return {"success": False, "final_recommendation": None, "llm_error_message": f"LLM Connection Error: {str(e)}"}
        except openai.APIStatusError as e:
            logger.error(f"LLM API Status Error in process_text: {e.status_code} - {e.response}")
            return {"success": False, "final_recommendation": None, "llm_error_message": f"LLM API Error: {e.status_code}"}
        except Exception as e:
            logger.error(f"Unexpected error in LLMClassifier.process_text: {str(e)}", exc_info=True)
            return {"success": False, "final_recommendation": None, "llm_error_message": f"Unexpected error: {str(e)}"}

    def _fallback_process_text(
        self,
        text: str,
        human_suggestions: Optional[Dict] = None,
        scoring_results: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Fallback method to process clinical text without an LLM using simpler rule-based extraction.

        Args:
            text: The clinical text to process
            human_suggestions: Optional dictionary of human suggestions to consider
            scoring_results: Optional dictionary containing pediatric scoring system results

        Returns:
            Dictionary with basic extracted information including scoring results if available
        """
        logger.info("Using rule-based fallback processing")

        # Initialize result
        demographics = {}
        chief_complaint = ""
        summary = ""
        vital_signs = {}
        suggested_care_level = "General"

        # Create final results structure
        result = {
            "demographics": demographics,
            "clinical_info": {
                "chief_complaint": chief_complaint,
                "summary": summary,
                "vital_signs": vital_signs,
            },
            "care_needs": {
                "suggested_care_level": suggested_care_level,
                "required_specialties": [],
            },
            "note": "Generated by rule-based fallback (no LLM connection)",
        }

        # Include scoring results if available
        if scoring_results:
            logger.info("Including pediatric scoring results in fallback assessment")
            result["scoring_results"] = scoring_results

            # Use scoring results to inform care level if available and not already specified by human
            if "recommended_care_levels" in scoring_results and not (
                human_suggestions and "care_level" in human_suggestions
            ):
                if scoring_results["recommended_care_levels"]:
                    result["care_needs"]["suggested_care_level"] = scoring_results[
                        "recommended_care_levels"
                    ][0]
                    result["care_needs"][
                        "care_level_reasoning"
                    ] = "Based on pediatric scoring systems"

                    # Include justifications from scoring
                    if "justifications" in scoring_results:
                        result["care_needs"]["score_justifications"] = scoring_results[
                            "justifications"
                        ]

        # Extract age using regex
        age_match = re.search(
            r"(\d+)(?:\s*-|\s+)(?:year|yr|y)[s\s]*(?:old)?", text, re.IGNORECASE
        )
        if age_match:
            result["demographics"]["age"] = int(age_match.group(1))

        # Extract gender
        if re.search(r"\b(?:male|boy|man)\b", text, re.IGNORECASE):
            result["demographics"]["gender"] = "male"
        elif re.search(r"\b(?:female|girl|woman)\b", text, re.IGNORECASE):
            result["demographics"]["gender"] = "female"

        # Extract vital signs
        vital_signs = {}

        # Heart rate
        hr_match = re.search(r"(?:HR|heart rate|pulse)[:\s]+(\d+)", text, re.IGNORECASE)
        if hr_match:
            vital_signs["hr"] = hr_match.group(1)

        # Respiratory rate
        rr_match = re.search(
            r"(?:RR|resp(?:iratory)? rate)[:\s]+(\d+)", text, re.IGNORECASE
        )
        if rr_match:
            vital_signs["rr"] = rr_match.group(1)

        # Blood pressure
        bp_match = re.search(
            r"(?:BP|blood pressure)[:\s]+(\d+)[/\\](\d+)", text, re.IGNORECASE
        )
        if bp_match:
            vital_signs["bp"] = f"{bp_match.group(1)}/{bp_match.group(2)}"

        # Temperature
        temp_match = re.search(
            r"(?:temp|temperature)[:\s]+(\d+\.?\d*)", text, re.IGNORECASE
        )
        if temp_match:
            vital_signs["temp"] = temp_match.group(1)

        # Oxygen saturation
        o2_match = re.search(
            r"(?:O2|oxygen|sat|saturation)[:\s]+(\d+)(?:\s*%)?", text, re.IGNORECASE
        )
        if o2_match:
            vital_signs["o2"] = f"{o2_match.group(1)}%"

        result["vital_signs"] = vital_signs

        # Extract keywords from text
        keywords = []
        potential_conditions = []

        # Look for key medical terms
        medical_terms = [
            "respiratory distress",
            "cardiac",
            "heart",
            "pneumonia",
            "sepsis",
            "seizure",
            "fever",
            "infection",
            "fracture",
            "trauma",
            "bleeding",
            "asthma",
            "bronchiolitis",
            "diabetes",
            "DKA",
            "cancer",
            "injury",
            "stroke",
            "neurological",
            "liver",
            "renal",
            "failure",
            "shock",
            "anemia",
            "meningitis",
            "appendicitis",
            "vomiting",
            "dehydration",
            "acute",
            "chronic",
            "critical",
            "ventilator",
            "monitor",
            "surgery",
        ]

        for term in medical_terms:
            if term.lower() in text.lower():
                keywords.append(term)

                # Check for specific conditions
                if term in ["pneumonia", "bronchiolitis", "asthma"]:
                    potential_conditions.append("Respiratory condition")
                elif term in ["cardiac", "heart"]:
                    potential_conditions.append("Cardiac condition")
                elif term in ["seizure", "neurological", "stroke"]:
                    potential_conditions.append("Neurological condition")
                elif term in ["infection", "sepsis", "fever", "meningitis"]:
                    potential_conditions.append("Infectious condition")
                elif term in ["trauma", "fracture", "injury", "bleeding"]:
                    potential_conditions.append("Trauma")

        # Remove duplicates
        keywords = list(set(keywords))
        potential_conditions = list(set(potential_conditions))

        result["keywords"] = keywords + potential_conditions

        # Try to extract a summary
        sentences = text.split(".")
        summary = ""
        if len(sentences) >= 2:
            summary = sentences[0].strip() + ". " + sentences[1].strip() + "."
        elif sentences:
            summary = sentences[0].strip() + "."

        # Determine a chief complaint (first sentence or summary)
        sentences = text.split(".")
        chief_complaint = sentences[0] if sentences else "Unknown"
        if len(chief_complaint) > 100:
            chief_complaint = chief_complaint[:100] + "..."

        # Consider human suggestions for care level
        suggested_care_level = "General"
        if human_suggestions and "care_level" in human_suggestions:
            care_levels = human_suggestions["care_level"]
            if "NICU" in care_levels:
                suggested_care_level = "NICU"
            elif "PICU" in care_levels:
                suggested_care_level = "PICU"
            elif "ICU" in care_levels:
                suggested_care_level = "ICU"
        else:
            # Try to determine care level from text and vital signs
            text_lower = text.lower()
            if (
                "nicu" in text_lower
                or "newborn" in text_lower
                or "neonate" in text_lower
                or "premature" in text_lower
            ):
                suggested_care_level = "NICU"
            elif "picu" in text_lower or "pediatric icu" in text_lower:
                suggested_care_level = "PICU"
            elif "icu" in text_lower or "intensive care" in text_lower:
                suggested_care_level = "ICU"
            elif (
                "respiratory distress" in text_lower
                or "intubated" in text_lower
                or "ventilator" in text_lower
                or "shock" in text_lower
                or "sepsis" in text_lower
            ):
                suggested_care_level = "ICU"

            # Check vital signs for critical values
            if vital_signs:
                hr = vital_signs.get("hr", "")
                if hr and hr.isdigit() and (int(hr) > 180 or int(hr) < 60):
                    suggested_care_level = "ICU"  # Extreme heart rate

                o2 = vital_signs.get("o2", "")
                if o2 and o2.strip("%").isdigit() and int(o2.strip("%")) < 90:
                    suggested_care_level = "ICU"  # Low oxygen saturation

        result["suggested_care_level"] = suggested_care_level
        result["chief_complaint"] = chief_complaint
        result["clinical_history"] = summary if summary else text[:200] + "..."

        return result


# Example usage in simulation mode (when run directly)
if __name__ == "__main__":
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)

    # Create classifier instance
    classifier = LLMClassifier()

    # Example clinical text
    example_text = """
    3-year-old male presenting with high fever (39.5°C), increased work of breathing,
    and decreased oral intake for the past 2 days. HR 145, RR 35, BP 90/60, SpO2 93% on RA.
    History of prematurity at 32 weeks, previous RSV bronchiolitis at 6 months requiring
    PICU admission and brief HFNC support. Currently on albuterol and ipratropium nebs
    with minimal improvement.
    """

    # Process the text
    try:
        print("Testing LLM classifier in simulation mode...")
        # Test model listing
        print("Available models:")
        models = classifier.refresh_models()
        print(models)

        # Test connection
        if models:
            success, message = classifier.test_connection(model=models[0])
            print(f"Connection test: {'Success' if success else 'Failed'} - {message}")

        # Process text
        results = classifier.process_text(example_text)
        print("\nResults:")
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Error running simulation: {str(e)}")
        print("Note: This module requires LM Studio to be running for actual use.")
        # Try fallback
        print("\nTrying fallback processing:")
        results = classifier._fallback_process_text(example_text, None)
        print(json.dumps(results, indent=2))
