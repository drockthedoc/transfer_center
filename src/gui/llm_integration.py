"""
LLM classifier integration for the Transfer Center GUI.

This module handles the integration with local LLM services through LM Studio's
OpenAI-compatible API for text classification and information extraction.
"""

import json
import logging
import os
import re
import sys
import traceback
from typing import Any, Dict, List, Optional

import openai

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

    def _setup_client(self) -> openai.OpenAI:
        """Set up the OpenAI client with the LM Studio API URL."""
        return openai.OpenAI(
            base_url=self.api_url,
            api_key="not-needed",  # LM Studio doesn't require an API key
        )

    def set_api_url(self, api_url: str):
        """Update the API URL and reinitialize the client."""
        self.api_url = api_url
        self.client = self._setup_client()
        self.refresh_models()

    def set_model(self, model: str):
        """Update the model name."""
        self.model = model

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
        try:
            # Instead of testing the full chat completion which can have streaming issues,
            # just check if we can list models which is a simpler API call
            logger.info(f"Checking API connection to {self.api_url}")

            # We already know models are available since we fetched them earlier
            if self.model in self.available_models:
                # Simple success if model is in the available models list
                logger.info(f"Connection verified: model {self.model} is available")
                return True, "Connection successful"
            else:
                # This should rarely happen since we select from available models
                logger.warning(f"Model {self.model} not found in available models")
                return (
                    False,
                    f"Model {
                        self.model} not found in available models: {
                        self.available_models}",
                )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Connection test failed: {error_msg}")

            # Provide more helpful error messages for common issues
            if "Unauthorized" in error_msg:
                return (
                    False,
                    "Authentication error. Check if LM Studio requires an API key.",
                )
            elif (
                "Connection refused" in error_msg
                or "Failed to establish a connection" in error_msg
            ):
                return (
                    False,
                    "Could not connect to the server. Make sure LM Studio is running and the URL is correct.",
                )
            elif "not found" in error_msg.lower() and self.model in error_msg:
                return (
                    False,
                    f"Model '{
                        self.model}' was not found. Check if it's loaded in LM Studio.",
                )
            else:
                return False, f"Error: {error_msg}"

    def _run_entity_extraction(self, text: str) -> Dict[str, Any]:
        """
        Step 1: Extract clinical entities from the text.

        Args:
            text: The clinical text to process

        Returns:
            Dictionary of extracted entities
        """
        # Create the system prompt for entity extraction
        system_prompt = """You are an expert clinical information extractor. Extract all relevant clinical information
        from the following patient vignette. Think step-by-step and be thorough, but only include information
        that is explicitly mentioned in the text.

        Format your response as a JSON object with the following structure:
        {
          "symptoms": [list of symptoms mentioned],
          "medical_problems": [list of medical problems or conditions mentioned],
          "medications": [list of medications mentioned],
          "vital_signs": {dictionary of vital signs with values},
          "demographics": {
            "age": patient age if mentioned,
            "weight": patient weight if mentioned (in kg),
            "sex": patient sex if mentioned
          },
          "medical_history": relevant past medical history,
          "clinical_context": additional clinical context like location, transport mode
        }
        """

        # Create the user prompt
        user_prompt = (
            f"Extract clinical information from this patient vignette:\n\n{text}"
        )

        try:
            # Make the API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}
                ],
                temperature=0.1,  # Low temperature for more deterministic results
                max_tokens=1000,
            )

            # Extract the response content
            response_content = response.choices[0].message.content
            logger.debug(f"Entity extraction response: {response_content}")

            # Try to parse the JSON response
            match = re.search(r"\{.*\}", response_content, re.DOTALL)
            if match:
                json_str = match.group(0)
                result = json.loads(json_str)
                return result
            else:
                logger.warning("Failed to parse JSON from entity extraction response")
                return {}
        except Exception as e:
            logger.error(f"Error in entity extraction: {str(e)}")
            return {}

    def _run_specialty_assessment(
        self, extracted_entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 2: Assess specialty needs based on extracted entities.

        Args:
            extracted_entities: Dictionary of extracted clinical entities

        Returns:
            Dictionary with specialty need assessment
        """
        # Define specialty indicators
        specialty_indicators = {
            "cardiology": ["heart", "cardiac", "chest pain", "arrhythmia", "murmur"],
            "neurology": ["seizure", "stroke", "headache", "neurological", "brain"],
            "pulmonology": ["respiratory", "breathing", "asthma", "pneumonia", "lungs"],
            "neonatology": ["newborn", "premature", "neonate", "NICU"],
            "orthopedics": ["fracture", "bone", "joint", "sprain", "musculoskeletal"],
            "gastroenterology": [
                "abdominal pain",
                "vomiting",
                "diarrhea",
                "GI bleed",
                "liver",
            ],
            "endocrinology": ["diabetes", "thyroid", "hormone", "glucose"],
            "infectious disease": ["infection", "sepsis", "meningitis", "cellulitis"],
            "hematology/oncology": [
                "cancer",
                "leukemia",
                "anemia",
                "bleeding",
                "oncology",
            ],
            "psychiatry": [
                "psychiatric",
                "depression",
                "anxiety",
                "mental health",
                "suicide",
            ],
        }

        # Format extracted entities as text for the prompt
        entities_text = json.dumps(extracted_entities, indent=2)

        # Format specialty indicators for the prompt
        indicators_text = "\n".join(
            [
                f"- {specialty}: {', '.join(indicators)}"
                for specialty, indicators in specialty_indicators.items()
            ]
        )

        # Create the system prompt for specialty assessment
        system_prompt = """You are an expert triage physician. Your task is to assess what medical specialties might be needed
        based on the clinical information provided. Think step-by-step about each potential specialty need.

        Format your response as a JSON object with the following structure:
        {
          "identified_specialties_needed": [
            {
              "specialty_name": "name of the specialty",
              "likelihood_score": numerical score from 0-100 indicating confidence,
              "supporting_evidence": "text explaining why this specialty is needed"
            },
            {...}
          ]
        }
        """

        # Create the user prompt
        user_prompt = f"""Based on these extracted clinical entities:

        {entities_text}

        And these specialty need indicators:
        {indicators_text}

        Identify which specialties might be needed for this patient. For each specialty, provide a likelihood score (0-100) and supporting evidence from the clinical information.
        """

        try:
            # Make the API call - LM Studio doesn't support 'system' role, so combine
            # into user message
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}
                ],
                temperature=0.1,  # Low temperature for more deterministic results
                max_tokens=1000,
            )

            # Extract the response content
            response_content = response.choices[0].message.content
            logger.debug(f"Specialty assessment response: {response_content}")

            # Try to parse the JSON response
            match = re.search(r"\{.*\}", response_content, re.DOTALL)
            if match:
                json_str = match.group(0)
                result = json.loads(json_str)
                return result
            else:
                logger.warning(
                    "Failed to parse JSON from specialty assessment response"
                )
                return {"identified_specialties_needed": []}
        except Exception as e:
            logger.error(f"Error in specialty assessment: {str(e)}")
            return {"identified_specialties_needed": []}

    def _run_exclusion_evaluation(
        self, extracted_entities: Dict[str, Any], exclusion_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 3: Evaluate exclusion criteria based on extracted entities.

        Args:
            extracted_entities: Dictionary of extracted clinical entities
            exclusion_criteria: Dictionary of exclusion criteria

        Returns:
            Dictionary with exclusion criteria evaluation
        """
        # Format extracted entities as text for the prompt
        entities_text = json.dumps(extracted_entities, indent=2)

        # Format exclusion criteria for the prompt
        exclusions_text = ""
        exclusion_id = 1

        # For simplicity, we'll focus on community campus exclusions
        for campus_key, campus_data in exclusion_criteria.get("campuses", {}).items():
            # General exclusions
            for exclusion in campus_data.get("general_exclusions", []):
                exclusions_text += f"#{exclusion_id}. GENERAL: {exclusion}\n"
                exclusion_id += 1

            # Department-specific exclusions
            for dept, dept_data in campus_data.get("departments", {}).items():
                for exclusion in dept_data.get("exclusions", []):
                    exclusions_text += f"#{exclusion_id}. {dept.upper()}: {exclusion}\n"
                    exclusion_id += 1

        # Create the system prompt for exclusion evaluation
        system_prompt = """You are an expert transfer center physician. Your task is to evaluate whether this patient meets any
        exclusion criteria for transfer. Think step-by-step for each criterion.

        Format your response as a JSON object with the following structure:
        {
          "exclusion_criteria_evaluation": [
            {
              "exclusion_rule_id": "identifier of the exclusion rule",
              "rule_text": "full text of the exclusion rule",
              "status": "one of: 'likely_met', 'likely_not_met', 'uncertain'",
              "confidence_score": numerical score from 0-100,
              "evidence_from_vignette": "text explaining the evidence for this status determination"
            },
            {...}
          ]
        }
        """

        # Create the user prompt
        user_prompt = f"""Based on these extracted clinical entities:

        {entities_text}

        Evaluate whether the patient meets any of the following exclusion criteria:

        {exclusions_text}

        For each numbered exclusion criterion, determine if it is 'likely_met', 'likely_not_met', or 'uncertain' based on the clinical information.
        Provide a confidence score (0-100) for your determination and cite specific evidence from the clinical information.
        """

        try:
            # Make the API call - LM Studio doesn't support 'system' role, so combine
            # into user message
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}
                ],
                temperature=0.1,  # Low temperature for more deterministic results
                max_tokens=1500,
            )

            # Extract the response content
            response_content = response.choices[0].message.content
            logger.debug(f"Exclusion evaluation response: {response_content}")

            # Try to parse the JSON response
            match = re.search(r"\{.*\}", response_content, re.DOTALL)
            if match:
                json_str = match.group(0)
                result = json.loads(json_str)
                return result
            else:
                logger.warning(
                    "Failed to parse JSON from exclusion evaluation response"
                )
                return {"exclusion_criteria_evaluation": []}
        except Exception as e:
            logger.error(f"Error in exclusion evaluation: {str(e)}")
            return {"exclusion_criteria_evaluation": []}

    def _run_final_recommendation(
        self,
        extracted_entities: Dict[str, Any],
        specialty_assessment: Dict[str, Any],
        exclusion_evaluation: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Step 4: Generate final recommendation based on previous steps.

        Args:
            extracted_entities: Dictionary of extracted clinical entities
            specialty_assessment: Dictionary with specialty need assessment
            exclusion_evaluation: Dictionary with exclusion criteria evaluation

        Returns:
            Dictionary with final recommendation
        """
        # Combine all previous outputs for the prompt
        combined_data = {
            "extracted_clinical_entities": extracted_entities,
            "identified_specialties_needed": specialty_assessment.get(
                "identified_specialties_needed", []
            ),
            "exclusion_criteria_evaluation": (
                exclusion_evaluation.get("exclusion_criteria_evaluation", [])
                if exclusion_evaluation
                else []
            ),
        }

        combined_text = json.dumps(combined_data, indent=2)

        # Create the system prompt for final recommendation
        system_prompt = """You are an expert transfer center physician making a final recommendation for patient transfer.
        Your task is to synthesize all the analysis done so far and recommend an appropriate care level.

        Format your response as a JSON object with the following structure:
        {
          "recommended_care_level": "one of: 'General', 'ICU', 'PICU', 'NICU'",
          "confidence": numerical score from 0-100,
          "explanation": "text explaining the overall recommendation"
        }
        """

        # Create the user prompt
        user_prompt = f"""Based on the combined analysis:

        {combined_text}

        Determine the most appropriate care level for this patient. Consider the clinical entities, specialty needs, and exclusion criteria evaluations.
        Provide a confidence score (0-100) for your recommendation and explain your reasoning in detail.
        """

        try:
            # Make the API call - LM Studio doesn't support 'system' role, so combine
            # into user message
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}
                ],
                temperature=0.1,  # Low temperature for more deterministic results
                max_tokens=1000,
            )

            # Extract the response content
            response_content = response.choices[0].message.content
            logger.debug(f"Final recommendation response: {response_content}")

            # Try to parse the JSON response
            match = re.search(r"\{.*\}", response_content, re.DOTALL)
            if match:
                json_str = match.group(0)
                result = json.loads(json_str)
                return result
            else:
                logger.warning(
                    "Failed to parse JSON from final recommendation response"
                )
                return {
                    "recommended_care_level": "General",
                    "confidence": 50,
                    "explanation": "Unable to determine a specific recommendation.",
                }
        except Exception as e:
            logger.error(f"Error in final recommendation: {str(e)}")
            return {
                "recommended_care_level": "General",
                "confidence": 50,
                "explanation": f"Error generating recommendation: {str(e)}",
            }

    def process_text(
        self, text: str, human_suggestions: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Process clinical text to extract structured information using a multi-step prompting approach.

        Args:
            text: The clinical text to process
            human_suggestions: Optional dictionary of human suggestions to consider

        Returns:
            Dictionary containing:
            - chief_complaint: Chief complaint extracted from text
            - clinical_history: Summarized clinical history
            - vital_signs: Dictionary of vital signs (e.g., hr, bp, rr, temp, o2)
            - age: Extracted patient age
            - weight_kg: Extracted patient weight in kg
            - sex: Extracted patient sex
            - keywords: List of important medical keywords
            - suggested_care_level: Suggested level of care
            - specialty_needs: List of specialty needs with likelihood and evidence
            - exclusion_matches: List of exclusion criteria matches with evidence
            - explainability: Detailed explanation of reasoning
        """
        # First try with the LLM prompt chain, if that fails fall back to
        # rule-based processing
        try:
            logger.info(
                f"Processing text with {
                    self.model} on {
                    self.api_url} using multi-step prompting"
            )

            # Step 1: Entity Extraction
            entity_result = self._run_entity_extraction(text)
            if not entity_result:
                raise ValueError("Entity extraction failed")

            # Step 2: Specialty Need Assessment
            specialty_result = self._run_specialty_assessment(entity_result)

            # Step 3: Exclusion Criteria Evaluation
            # Load exclusion criteria - assuming it's in the standard location
            exclusion_criteria_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data",
                "exclusion_criteria_clean.json",
            )
            exclusion_criteria = {}
            try:
                with open(exclusion_criteria_path, "r") as f:
                    exclusion_criteria = json.load(f)
            except Exception as e:
                logger.error(f"Error loading exclusion criteria: {str(e)}")
                # Continue without exclusion criteria

            # Only run exclusion evaluation if we have criteria
            exclusion_result = None
            if exclusion_criteria:
                exclusion_result = self._run_exclusion_evaluation(
                    entity_result, exclusion_criteria
                )

            # Step 4: Final Recommendation
            recommendation_result = self._run_final_recommendation(
                entity_result, specialty_result, exclusion_result
            )

            # Combine results into the expected format for the application
            result = {
                "chief_complaint": (
                    entity_result.get("medical_problems", ["Unknown"])[0]
                    if entity_result.get("medical_problems")
                    else (
                        entity_result.get("symptoms", ["Unknown"])[0]
                        if entity_result.get("symptoms")
                        else "Unknown"
                    )
                ),
                "clinical_history": entity_result.get(
                    "medical_history", text[:200] + "..."
                ),
                "vital_signs": entity_result.get("vital_signs", {}),
                "age": entity_result.get("demographics", {}).get("age"),
                "weight_kg": entity_result.get("demographics", {}).get("weight"),
                "sex": entity_result.get("demographics", {}).get("sex"),
                "keywords": entity_result.get("symptoms", [])
                + entity_result.get("medical_problems", []),
                "suggested_care_level": recommendation_result.get(
                    "recommended_care_level", "General"
                ),
                "note": f"Generated by {self.model} using multi-step prompting",
                # New fields from the prompt chain
                "specialty_needs": specialty_result.get(
                    "identified_specialties_needed", []
                ),
                "exclusion_matches": (
                    exclusion_result.get("exclusion_criteria_evaluation", [])
                    if exclusion_result
                    else []
                ),
                "explainability": {
                    "reasoning": recommendation_result.get("explanation", ""),
                    "confidence": recommendation_result.get("confidence", 0),
                },
            }

            # Consider human suggestions
            if human_suggestions and "care_level" in human_suggestions:
                # If human suggestions include NICU, PICU, or ICU, consider those
                care_levels = human_suggestions["care_level"]
                if "NICU" in care_levels:
                    result["suggested_care_level"] = "NICU"
                elif "PICU" in care_levels:
                    result["suggested_care_level"] = "PICU"
                elif "ICU" in care_levels:
                    result["suggested_care_level"] = "ICU"

            logger.info("Successfully processed text with LLM prompt chain")
            return result

        except Exception as e:
            logger.error(f"Error processing text with LLM prompt chain: {str(e)}")
            logger.error(traceback.format_exc())
            logger.info("Falling back to rule-based processing")
            return self._fallback_process_text(text, human_suggestions)

    def _fallback_process_text(
        self, text: str, human_suggestions: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Fallback method to process clinical text without an LLM using simpler rule-based extraction.

        Args:
            text: The clinical text to process
            human_suggestions: Optional dictionary of human suggestions to consider

        Returns:
            Dictionary with basic extracted information
        """
        from src.llm.classification import parse_patient_text

        # Use the built-in parser function from the project
        parsed_info = parse_patient_text(text)

        # Extract relevant pieces
        potential_conditions = parsed_info.get("potential_conditions", [])
        keywords = parsed_info.get("identified_keywords", [])
        vital_signs = parsed_info.get("extracted_vital_signs", {})
        summary = parsed_info.get("raw_text_summary", "")

        # Enhanced vital signs extraction with regex
        if not vital_signs:
            # Try additional regex patterns for vital signs
            hr_match = re.search(
                r"(?:HR|heart rate|pulse)[:\s]*([0-9]{2,3})\b", text, re.IGNORECASE
            )
            if hr_match:
                vital_signs["hr"] = hr_match.group(1)

            bp_match = re.search(
                r"(?:BP|blood pressure)[:\s]*([0-9]{2,3})[\s/]*([0-9]{2,3})\b",
                text,
                re.IGNORECASE,
            )
            if bp_match:
                vital_signs["bp"] = f"{bp_match.group(1)}/{bp_match.group(2)}"

            rr_match = re.search(
                r"(?:RR|resp|respiratory rate)[:\s]*([0-9]{1,2})\b", text, re.IGNORECASE
            )
            if rr_match:
                vital_signs["rr"] = rr_match.group(1)

            o2_match = re.search(
                r"(?:O2|SpO2|oxygen|sat)[:\s]*([0-9]{1,3})\s*%?\b", text, re.IGNORECASE
            )
            if o2_match:
                vital_signs["o2"] = o2_match.group(1) + "%"

            temp_match = re.search(
                r"(?:T|temp|temperature)[:\s]*([0-9]{2}(?:\.[0-9])?)\s*(?:C|F)?\b",
                text,
                re.IGNORECASE,
            )
            if temp_match:
                vital_signs["temp"] = temp_match.group(1) + "°C"

        # Enhanced keyword extraction
        if not keywords and not potential_conditions:
            # Common pediatric conditions to check for
            pediatric_keywords = [
                "bronchiolitis",
                "rsv",
                "pneumonia",
                "asthma",
                "croup",
                "febrile",
                "sepsis",
                "dehydration",
                "seizure",
                "trauma",
                "fracture",
                "respiratory distress",
                "failure to thrive",
                "intubation",
                "ventilator",
                "shock",
                "meningitis",
            ]

            for keyword in pediatric_keywords:
                if keyword in text.lower():
                    keywords.append(keyword)

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

        return {
            "chief_complaint": chief_complaint,
            "clinical_history": summary if summary else text[:200] + "...",
            "vital_signs": vital_signs,
            "keywords": keywords + potential_conditions,
            "suggested_care_level": suggested_care_level,
            "note": "Generated by rule-based system",
        }


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
