"""Recommendation component for LLM integration.

This module handles the generation of final recommendations based on all previous assessments.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from src.core.models import Recommendation
from src.llm.utils import robust_json_parser

logger = logging.getLogger(__name__)


class RecommendationGenerator:
    """Handles generation of final recommendations based on all previous assessments."""

    def __init__(self, client, model: str):
        """
        Initialize the recommendation generator.

        Args:
            client: OpenAI client instance
            model: Name of the model to use
        """
        self.client = client
        self.model = model

    def generate_recommendation(
        self,
        extracted_entities: Dict[str, Any],
        specialty_assessment: Dict[str, Any],
        exclusion_evaluation: Optional[Dict[str, Any]] = None,
    ) -> Recommendation:
        """Generate final recommendation based on previous steps.

        Args:
            extracted_entities: Dictionary of extracted clinical entities
            specialty_assessment: Dictionary with specialty need assessment
            exclusion_evaluation: Optional dictionary with exclusion criteria evaluation

        Returns:
            Dictionary with final recommendation
        """
        """
        Generate final recommendation based on previous steps.

        Args:
            extracted_entities: Dictionary of extracted clinical entities
            specialty_assessment: Dictionary with specialty need assessment
            exclusion_evaluation: Optional dictionary with exclusion criteria evaluation

        Returns:
            Dictionary with final recommendation
        """
        logger.info("Generating final recommendation...")

        # First try with the LLM approach
        llm_result = self._try_llm_recommendation(
            extracted_entities, specialty_assessment, exclusion_evaluation
        )

        # Always return the LLM recommendation if it's available - no fallback to rule-based
        if llm_result:
            return llm_result

        # If LLM approach fails completely, log the error and return a basic error recommendation
        logger.error("LLM recommendation generation failed completely")
        return Recommendation(
            transfer_request_id="error",
            recommended_campus_id="ERROR",
            confidence_score=0,
            reason="Failed to generate a recommendation with the LLM",
            notes=["LLM error - please check the logs and try again"],
        )

    def _try_llm_recommendation(
        self,
        extracted_entities: Dict[str, Any],
        specialty_assessment: Dict[str, Any],
        exclusion_evaluation: Optional[Dict[str, Any]] = None,
    ) -> Optional[Recommendation]:
        """Detailed logging has been added to diagnose recommendation issues."""
        """
        Attempt to generate a recommendation using the LLM with JSON schema.
        
        Args:
            extracted_entities: Dictionary of extracted clinical entities
            specialty_assessment: Dictionary with specialty need assessment
            exclusion_evaluation: Optional dictionary with exclusion criteria evaluation
            
        Returns:
            Dictionary with recommendation or None if failed
        """
        try:
            # Log input data for debugging
            logger.info(f"===== RECOMMENDATION GENERATION INPUTS =====\n")
            logger.info(
                f"EXTRACTED ENTITIES: {json.dumps(extracted_entities, indent=2)[:1000]}...\n"
            )
            logger.info(
                f"SPECIALTY ASSESSMENT: {json.dumps(specialty_assessment, indent=2)[:1000]}...\n"
            )
            if exclusion_evaluation:
                logger.info(
                    f"EXCLUSION EVALUATION: {json.dumps(exclusion_evaluation, indent=2)[:1000]}...\n"
                )
            else:
                logger.info("EXCLUSION EVALUATION: None\n")

            # Construct the prompt for recommendation generation
            prompt = self._build_recommendation_prompt(
                extracted_entities, specialty_assessment, exclusion_evaluation
            )

            # Log the prompt for debugging
            logger.info(
                f"===== RECOMMENDATION PROMPT =====\n{prompt[:1000]}...\n[truncated]"
            )

            # Define JSON schema to enforce structure following LM Studio format
            json_schema = {
                "type": "json_schema",
                "json_schema": {
                    "name": "recommendation",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "recommended_campus": {
                                "type": "string",
                                "description": "The name of the recommended hospital campus",
                            },
                            "care_level": {
                                "type": "string",
                                "enum": [
                                    "general_floor",
                                    "intermediate_care",
                                    "picu",
                                    "nicu",
                                ],
                                "description": "The minimum appropriate care level needed for this patient",
                            },
                            "confidence_score": {
                                "type": "number",
                                "description": "Confidence score for this recommendation (0-100)",
                            },
                            "clinical_reasoning": {
                                "type": "string",
                                "description": "Clear explanation of why this campus and care level are appropriate (not overrecommending)",
                            },
                            "urgency": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "critical"],
                                "description": "The urgency level for this transfer based on patient stability",
                            },
                            "campus_scores": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "found": {"type": "boolean"},
                                    },
                                },
                                "description": "List of exclusion criteria checked and whether any were found",
                            },
                            "bed_availability": {
                                "type": "object",
                                "properties": {
                                    "confirmed": {"type": "boolean"},
                                    "details": {"type": "string"},
                                },
                                "description": "Confirmation of bed availability",
                            },
                            "traffic_report": {
                                "type": "string",
                                "description": "Current traffic conditions affecting transport",
                            },
                            "weather_report": {
                                "type": "string",
                                "description": "Current weather conditions affecting transport",
                            },
                            "addresses": {
                                "type": "object",
                                "properties": {
                                    "origin": {"type": "string"},
                                    "destination": {"type": "string"},
                                },
                                "description": "Street addresses for origin and destination",
                            },
                            "eta": {
                                "type": "object",
                                "properties": {
                                    "minutes": {"type": "number"},
                                    "transport_mode": {"type": "string"},
                                },
                                "description": "Estimated time of arrival in minutes and transport mode",
                            },
                            "required_specialties": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of specialties needed for this patient",
                            },
                            "campus_scores": {
                                "type": "object",
                                "properties": {
                                    "primary": {
                                        "type": "object",
                                        "properties": {
                                            "care_level_match": {"type": "number"},
                                            "specialty_availability": {
                                                "type": "number"
                                            },
                                            "capacity": {"type": "number"},
                                            "location": {"type": "number"},
                                            "specific_resources": {"type": "number"},
                                        },
                                    },
                                    "backup": {
                                        "type": "object",
                                        "properties": {
                                            "care_level_match": {"type": "number"},
                                            "specialty_availability": {
                                                "type": "number"
                                            },
                                            "capacity": {"type": "number"},
                                            "location": {"type": "number"},
                                            "specific_resources": {"type": "number"},
                                        },
                                    },
                                },
                                "description": "Scores for primary and backup campuses on various criteria",
                            },
                            "transport_considerations": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Considerations for patient transport",
                            },
                            "required_resources": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of resources needed for this patient",
                            },
                            "clinical_summary": {
                                "type": "string",
                                "description": "Concise summary of the patient's clinical condition and needs",
                            },
                        },
                        "required": [
                            "recommended_campus",
                            "confidence_score",
                            "care_level",
                            "clinical_reasoning",
                            "exclusions_checked",
                            "bed_availability",
                            "traffic_report",
                            "weather_report",
                            "addresses",
                            "eta",
                            "required_specialties",
                            "campus_scores",
                            "transport_considerations",
                            "required_resources",
                            "clinical_summary",
                        ],
                    },
                },
            }

            logger.info("Attempting recommendation with JSON schema structure")

            # Try using the structured output approach
            try:
                # Call the LLM with JSON schema to enforce structure
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a hospital transfer coordinator providing recommendations in a structured format.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,  # Keep temperature low for consistency
                    max_tokens=2048,  # Sufficient tokens while keeping reasonable
                    response_format=json_schema,
                )
                logger.info("Successfully used structured output schema")
            except Exception as schema_error:
                # Handle the case where LM Studio doesn't support structured output
                logger.warning(f"Structured output not supported: {str(schema_error)}")
                logger.info("Falling back to standard approach with JSON instructions")

                # Add explicit JSON formatting instructions to the prompt
                json_instructions = (
                    "\n\nIMPORTANT: Your response MUST be in valid JSON format and conform to this schema:\n"
                    "```json\n"
                    "{"
                    '\n  "recommended_campus": "Hospital campus name",'
                    '\n  "confidence_score": number between 0-100,'
                    '\n  "backup_campus": "Backup hospital campus name",'
                    '\n  "backup_confidence_score": number between 0-100,'
                    '\n  "care_level": "general_floor" | "intermediate_care" | "picu" | "nicu",'
                    '\n  "clinical_reasoning": "Brief clinical justification...",'
                    '\n  "exclusions_checked": ['
                    '\n    { "name": "Exclusion criterion name", "found": boolean },'
                    "\n    ..."
                    "\n  ],"
                    '\n  "bed_availability": {'
                    '\n    "confirmed": boolean,'
                    '\n    "details": "Bed availability details"'
                    "\n  },"
                    '\n  "traffic_report": "Current traffic conditions",'
                    '\n  "weather_report": "Current weather conditions",'
                    '\n  "addresses": {'
                    '\n    "origin": "Street address of current location",'
                    '\n    "destination": "Street address of destination"'
                    "\n  },"
                    '\n  "eta": {'
                    '\n    "minutes": number,'
                    '\n    "transport_mode": "Transport mode"'
                    "\n  },"
                    '\n  "required_specialties": ["specialty1", "specialty2", ...],'
                    '\n  "campus_scores": {'
                    '\n    "primary": {'
                    '\n      "care_level_match": number between 1-5,'
                    '\n      "specialty_availability": number between 1-5,'
                    '\n      "capacity": number between 1-5,'
                    '\n      "location": number between 1-5,'
                    '\n      "specific_resources": number between 1-5'
                    "\n    },"
                    '\n    "backup": {'
                    '\n      "care_level_match": number between 1-5,'
                    '\n      "specialty_availability": number between 1-5,'
                    '\n      "capacity": number between 1-5,'
                    '\n      "location": number between 1-5,'
                    '\n      "specific_resources": number between 1-5'
                    "\n    }"
                    "\n  },"
                    '\n  "transport_considerations": ["consideration1", ...],'
                    '\n  "required_resources": ["resource1", ...],'
                    '\n  "clinical_summary": "Concise summary..."'
                    "\n}"
                    "\n```\n"
                    "Ensure your JSON conforms EXACTLY to this schema and is valid."
                )

                # Call the LLM with explicit JSON formatting instructions
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a hospital transfer coordinator. Respond ONLY with valid JSON.",
                        },
                        {"role": "user", "content": prompt + json_instructions},
                    ],
                    temperature=0.1,
                    max_tokens=2048,
                )

            # Extract response content
            content = response.choices[0].message.content
            logger.debug(f"Raw LLM response (truncated): {content[:500]}...")

            # Check for response truncation
            finish_reason = response.choices[0].finish_reason
            if finish_reason == "length":
                logger.warning(
                    f"LLM response was truncated (finish_reason={finish_reason})"
                )

            # Try to parse the JSON response
            try:
                recommendation_json = robust_json_parser.extract_and_parse_json(content)

                # Log the parsed structure
                logger.info(
                    f"===== RECOMMENDATION JSON RESPONSE =====\n{json.dumps(recommendation_json, indent=2)}\n"
                )

                # Validate the response has required fields
                required_fields = [
                    "recommended_campus",
                    "confidence_score",
                    "backup_campus",
                    "backup_confidence_score",
                    "care_level",
                    "exclusions_checked",
                    "addresses",
                    "eta",
                ]
                missing_fields = [
                    field
                    for field in required_fields
                    if field not in recommendation_json
                ]

                if missing_fields:
                    logger.error(
                        f"===== MISSING REQUIRED FIELDS IN RECOMMENDATION =====\n{missing_fields}"
                    )
                    logger.error(
                        "Will attempt to generate recommendation anyway, but it may be incomplete"
                    )

                # Check if exclusions were found
                if "exclusions_checked" in recommendation_json:
                    found_exclusions = [
                        ex["name"]
                        for ex in recommendation_json["exclusions_checked"]
                        if ex.get("found", False)
                    ]
                    if found_exclusions:
                        logger.warning(
                            f"===== EXCLUSIONS FOUND =====\n{found_exclusions}"
                        )

                # Log proximity and backup information
                if "addresses" in recommendation_json and "eta" in recommendation_json:
                    logger.info(f"===== PROXIMITY DATA =====")
                    logger.info(
                        f"Origin: {recommendation_json['addresses'].get('origin', 'Unknown')}"
                    )
                    logger.info(
                        f"Destination: {recommendation_json['addresses'].get('destination', 'Unknown')}"
                    )
                    logger.info(
                        f"ETA: {recommendation_json['eta'].get('minutes', 'Unknown')} minutes via {recommendation_json['eta'].get('transport_mode', 'Unknown')}"
                    )

                # Log backup recommendation
                if (
                    "backup_campus" in recommendation_json
                    and "backup_confidence_score" in recommendation_json
                ):
                    logger.info(f"===== BACKUP RECOMMENDATION =====")
                    logger.info(
                        f"Backup Campus: {recommendation_json['backup_campus']}"
                    )
                    logger.info(
                        f"Backup Confidence: {recommendation_json['backup_confidence_score']}%"
                    )

                # Log care level justification
                if (
                    "clinical_reasoning" in recommendation_json
                    and "care_level" in recommendation_json
                ):
                    logger.info(
                        f"===== CARE LEVEL JUSTIFICATION =====\n{recommendation_json['care_level']}: {recommendation_json['clinical_reasoning']}"
                    )

                # Convert the JSON response to a Recommendation object
                recommendation_obj = self._convert_to_recommendation(
                    recommendation_json
                )
                logger.info(
                    f"===== FINAL RECOMMENDATION OBJECT =====\n{recommendation_obj}\n"
                )
                return recommendation_obj

            except (json.JSONDecodeError, ValueError, AttributeError) as e:
                logger.error(f"===== JSON PARSING FAILED =====\n{str(e)}")
                logger.error(f"Raw response content: {content[:500]}...")
                return None

        except Exception as e:
            logger.error(f"Error in LLM recommendation with schema: {str(e)}")
            logger.error(f"Error details: {type(e).__name__}")
            return None

    def _build_recommendation_prompt(
        self,
        extracted_entities: Dict[str, Any],
        specialty_assessment: Dict[str, Any],
        exclusion_evaluation: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build the prompt for recommendation generation with optimized token usage.

        Args:
            extracted_entities: Dictionary of extracted clinical entities
            specialty_assessment: Dictionary with specialty need assessment
            exclusion_evaluation: Optional dictionary with exclusion criteria evaluation

        Returns:
            Formatted prompt string optimized for token efficiency
        """
        # Extract only the essential information to reduce token count
        essential_patient_info = self._extract_essential_patient_info(
            extracted_entities
        )
        essential_specialty_info = self._extract_essential_specialty_info(
            specialty_assessment
        )
        essential_exclusion_info = self._extract_essential_exclusion_info(
            exclusion_evaluation
        )

        # Extract scoring results if available
        scoring_results_str = ""
        if "scoring_results" in specialty_assessment:
            scoring_results = specialty_assessment["scoring_results"]
            scoring_results_str = "## SCORING RESULTS\n"

            # Add the scores section
            if "scores" in scoring_results:
                scoring_results_str += "### Clinical Scores:\n"
                for score_name, score_data in scoring_results["scores"].items():
                    if score_data != "N/A" and isinstance(
                        score_data.get("score"), (int, float)
                    ):
                        scoring_results_str += (
                            f"- {score_name.upper()}: {score_data['score']}\n"
                        )
                        if "interpretation" in score_data:
                            scoring_results_str += (
                                f"  Interpretation: {score_data['interpretation']}\n"
                            )

            # Add recommended care levels
            if "recommended_care_levels" in scoring_results:
                scoring_results_str += (
                    "\n### Recommended Care Levels (based on scores):\n"
                )
                scoring_results_str += (
                    ", ".join(scoring_results["recommended_care_levels"]) + "\n"
                )

            # Add justifications
            if "justifications" in scoring_results:
                scoring_results_str += "\n### Score Justifications:\n"
                for justification in scoring_results["justifications"]:
                    scoring_results_str += f"- {justification}\n"

        # Include travel and weather data if available
        travel_data_str = ""
        if "travel_data" in extracted_entities:
            travel_data = extracted_entities["travel_data"]
            travel_data_str = "## TRAVEL & LOCATION DATA\n"

            if "road_traffic" in travel_data:
                travel_data_str += f"Road Traffic: {travel_data['road_traffic']}\n"

            if "weather" in travel_data:
                travel_data_str += f"Weather Conditions: {travel_data['weather']}\n"

            if "current_address" in travel_data:
                travel_data_str += (
                    f"Current Location: {travel_data['current_address']}\n"
                )

            if "distance_estimates" in travel_data:
                travel_data_str += "\nDistance Estimates:\n"
                for campus, estimate in travel_data["distance_estimates"].items():
                    travel_data_str += f"- To {campus}: {estimate['distance']} miles, ETA: {estimate['eta']} minutes\n"

        # List available hospital campuses with their capabilities
        hospitals = [
            {
                "name": "Texas Children's Hospital - Main Campus (MC)",
                "capabilities": {
                    "PICU": "Advanced (highest level of pediatric critical care)",
                    "NICU": "Level IV (highest level of neonatal care)",
                    "Trauma": "Level I Pediatric Trauma Center",
                    "Specialists": "Comprehensive coverage across all pediatric specialties",
                    "Surgery": "Advanced pediatric surgery capabilities, including transplant",
                    "Cardiology": "Full pediatric cardiac services including heart transplant",
                    "Neurology": "Comprehensive pediatric neurology and neurosurgery",
                    "Oncology": "Complete pediatric cancer center",
                    "Capacity": "Largest bed capacity in the system",
                },
            },
            {
                "name": "Texas Children's Hospital - The Woodlands",
                "capabilities": {
                    "PICU": "Standard pediatric intensive care services",
                    "NICU": "Level III",
                    "Trauma": "Level II Pediatric Trauma Center",
                    "Specialists": "Good coverage of common specialties",
                    "Surgery": "General pediatric surgery",
                    "Cardiology": "Basic pediatric cardiology services",
                    "Neurology": "Basic pediatric neurology services",
                    "Capacity": "Medium capacity",
                },
            },
            {
                "name": "Texas Children's Hospital - West Campus (Katy)",
                "capabilities": {
                    "PICU": "Standard pediatric intensive care services",
                    "NICU": "Level III",
                    "Trauma": "Level II Pediatric Trauma Center",
                    "Specialists": "Good coverage of common specialties",
                    "Surgery": "General pediatric surgery",
                    "Cardiology": "Basic pediatric cardiology services",
                    "Neurology": "Basic pediatric neurology services",
                    "Capacity": "Medium capacity",
                },
            },
            {
                "name": "Texas Children's Hospital - North Austin Campus",
                "capabilities": {
                    "PICU": "Standard pediatric intensive care services",
                    "NICU": "Level III",
                    "Trauma": "Level III Pediatric Trauma Center",
                    "Specialists": "Limited specialty coverage",
                    "Surgery": "Basic pediatric surgery",
                    "Capacity": "Smaller capacity",
                },
            },
            {
                "name": "Texas Children's Hospital - Pavilion for Women",
                "capabilities": {
                    "NICU": "Level IV",
                    "Specialists": "Maternal-fetal medicine specialists",
                    "Surgery": "Neonatal surgery",
                    "Capacity": "Specialized for maternal and neonatal care only",
                },
            },
        ]

        # Convert to string representation
        hospitals_str = "Available Hospital Campuses:\n"
        for hospital in hospitals:
            hospitals_str += f"\n{hospital['name']}:\n"
            for capability, level in hospital["capabilities"].items():
                hospitals_str += f"  - {capability}: {level}\n"

        return f"""
## RECOMMENDATION TASK
You are a pediatric transfer coordinator making a recommendation for the optimal hospital campus 
for a pediatric patient transfer. Using ONLY the information provided and your medical expertise, 
generate a recommendation that balances clinical needs, bed availability, and geographic practicality.

## PATIENT INFORMATION
{essential_patient_info}

## SPECIALTY NEEDS
{essential_specialty_info}

{scoring_results_str}

## EXCLUSION CRITERIA
{essential_exclusion_info}

{travel_data_str}

## AVAILABLE HOSPITAL CAMPUSES
{hospitals_str}

## CARE LEVEL ASSESSMENT CRITERIA
Use this structured approach to determine required care level:

1. GENERAL PEDIATRIC FLOOR (Standard care):
   - Stable vital signs
   - No respiratory distress
   - No specialized monitoring needed
   - Manageable with standard nursing care

2. INTERMEDIATE CARE:
   - Requires more frequent monitoring than general floor
   - Mild respiratory support (e.g., nasal cannula oxygen)
   - Stable but requires closer observation

3. PICU (Pediatric Intensive Care): [RESERVE FOR TRULY CRITICAL PATIENTS ONLY]
   - MUST HAVE AT LEAST ONE OF THESE SPECIFIC INDICATIONS TO QUALIFY FOR PICU:
     * Respiratory failure requiring ventilator support (non-invasive or invasive)
     * Hemodynamic instability requiring vasopressors or continuous fluid resuscitation
     * Severe neurological compromise (GCS < 8, status epilepticus, increasing ICP)
     * Documented organ failure (not just risk of failure)
     * Immediate post-op from major surgery with unstable vital signs
     * Specific critical care interventions that cannot be provided on a regular floor
   - IMPORTANT: PICU beds are a precious resource. Common conditions like bronchiolitis, 
     Kawasaki disease without coronary involvement, DKA without altered mental status, 
     or fever without instability do NOT automatically require PICU

4. NICU (Neonatal Intensive Care):
   - Premature infants requiring intensive support
   - Term newborns with significant respiratory/cardiac issues
   - Congenital anomalies requiring immediate intervention

## SPECIALIST NEED ASSESSMENT
Only recommend specialists when truly needed:
   - Common conditions (e.g., uncomplicated pneumonia, dehydration) typically do NOT require specialists
   - Specialists should be recommended only for complex or rare conditions
   - The Main Campus has ALL specialties and is the default for complex cases
   - Regional campuses have good coverage of common specialties

## CAMPUS SELECTION CRITERIA
Score each campus on a scale of 1-5 for this specific patient with LOCATION GIVEN HIGHEST PRIORITY:

1. LOCATION: [HIGHEST PRIORITY FACTOR] Proximity to patient's current location
   - Score 5: Closest facility (<30 min transport time)
   - Score 4: Moderately close (30-45 min transport time)
   - Score 3: Further away (45-60 min transport time) 
   - Score 2: Distant (60-90 min transport time)
   - Score 1: Very distant (>90 min transport time)
   - CRITICAL: When all other factors are equal, ALWAYS choose the closest facility

2. CARE LEVEL MATCH: Does the campus provide the MINIMUM appropriate care level needed?
   - IMPORTANT: Do NOT recommend higher level of care than needed (e.g., PICU when intermediate care would suffice)
   - Regional campuses should be utilized for non-complex cases that meet their capabilities

3. SPECIALTY AVAILABILITY: Are needed specialists available? 
   - Only consider specialists that are TRULY REQUIRED for immediate care
   - If specialists are not immediately needed, all campuses score 5

4. CAPACITY: Consider bed availability (never recommend a facility with zero beds)

5. SPECIFIC RESOURCES: Special equipment or services required for this specific case

Follow this critical reasoning chain in detail:
1. First analyze the patient's condition and determine MINIMUM appropriate care level needed
   - Be conservative with PICU recommendations - only the sickest patients need PICU
   - Base care level on objective clinical criteria, not just diagnosis

2. Calculate distance/travel time to each campus from the patient's location
   - This is a CRITICAL factor - proximity should be weighted heavily
   - Explicitly compare travel times between campuses

3. Identify if specialists are truly required for IMMEDIATE care (not just eventually helpful)
   - Most common pediatric conditions can be managed without specialists

4. Score each campus using the criteria above with LOCATION given highest priority
   - Campus scores should reflect the actual travel times provided

5. Recommend the campus with the best balance of proximity and appropriate care level
   - Proximity should be the deciding factor when care level needs are met

6. CRITICAL: Provide a SPECIFIC backup campus with detailed reasoning
   - Explain why the backup was chosen over other options

7. CRITICAL: For each campus not chosen, provide specific reasons why it was excluded
   - ALWAYS explain why a closer campus was bypassed if a farther one was chosen
   - Include specific distance/time comparisons in this justification

Your recommendation must include:
- A specific recommended hospital campus from the list above
- A specific backup campus recommendation
- Confidence score (percentage 0-100%) for both primary and backup recommendations
- Care level needed (general_floor, intermediate_care, picu, or nicu)
- Brief clinical justification for the recommendation
- List of exclusions checked and whether any were found
- Confirmation of bed availability
- Current traffic conditions affecting transport
- Current weather conditions affecting transport
- Street addresses for origin and destination
- Estimated time of arrival (ETA) in minutes and transport mode
- List of specialties needed for this patient
- Scores for primary and backup campuses on various criteria
- Considerations for patient transport
- List of resources needed for this patient
- Concise summary of the patient's clinical condition and needs

This recommendation will directly inform critical patient transfer decisions.
"""

    def _extract_essential_patient_info(self, entities: Dict[str, Any]) -> str:
        """Extract the most relevant patient information in a concise format."""
        if not entities:
            return "No patient information available"

        # Extract demographics
        demographics = entities.get("demographics", {})
        age = demographics.get("age", "?")
        gender = demographics.get("gender", "?")

        # Extract clinical info
        clinical_info = entities.get("clinical_info", {})
        chief_complaint = clinical_info.get("chief_complaint", "No chief complaint")

        # Extract vital signs if available
        vitals = entities.get("vital_signs", {})
        vital_str = ""
        if vitals:
            vital_items = []
            for k, v in vitals.items():
                if v is not None:
                    vital_items.append(f"{k}: {v}")
            if vital_items:
                vital_str = "\nVitals: " + ", ".join(vital_items)

        # Extract diagnoses
        diagnoses = entities.get("diagnoses", [])
        diagnosis_str = "\nDiagnoses: " + ", ".join(diagnoses) if diagnoses else ""

        # Combine into concise summary
        return f"{age} y.o. {gender}, {chief_complaint}{vital_str}{diagnosis_str}"

    def _extract_essential_specialty_info(self, assessment: Dict[str, Any]) -> str:
        """Extract the most relevant specialty assessment information."""
        if not assessment:
            return "No specialty assessment available"

        # Extract recommended care level
        care_level = assessment.get("recommended_care_level", "Unknown")

        # Extract required specialties
        specialties = []
        for spec in assessment.get("required_specialties", []):
            if isinstance(spec, dict) and "specialty" in spec:
                importance = spec.get("importance", "")
                specialties.append(
                    f"{spec['specialty']} ({importance})"
                    if importance
                    else spec["specialty"]
                )

        specialty_str = (
            "\nSpecialties: " + ", ".join(specialties) if specialties else ""
        )

        # Extract potential conditions
        conditions = assessment.get("potential_conditions", [])
        condition_str = "\nConditions: " + ", ".join(conditions) if conditions else ""

        return f"Care Level: {care_level}{specialty_str}{condition_str}"

    def _extract_essential_exclusion_info(
        self, exclusion: Optional[Dict[str, Any]]
    ) -> str:
        """Extract essential exclusion information."""
        if not exclusion:
            return "No exclusion criteria applied"

        # Check if there are any exclusions
        excluded_campuses = exclusion.get("excluded_campuses", [])
        if not excluded_campuses:
            return "No campuses excluded"

        # Format exclusion reasons concisely
        exclusion_reasons = []
        for campus in excluded_campuses:
            name = campus.get("campus_name", "?")
            reason = campus.get("reason", "unknown reason")
            exclusion_reasons.append(f"{name}: {reason}")

        return "\n".join(exclusion_reasons)

    def _convert_to_recommendation(
        self, recommendation_json: Dict[str, Any]
    ) -> Recommendation:
        """
        Convert the LLM recommendation JSON response to a Recommendation object.

        Args:
            recommendation_json: The parsed JSON response from the LLM

        Returns:
            Recommendation object with the appropriate fields populated
        """
        try:
            logger.info(
                f"Processing LLM recommendation: {json.dumps(recommendation_json, indent=2)[:1000]}..."
            )

            # Extract primary campus name
            campus_name = recommendation_json.get(
                "recommended_campus", "No specific campus recommended"
            )

            # Extract backup campus if available
            backup_campus = recommendation_json.get(
                "backup_campus", "No backup campus specified"
            )
            backup_confidence = float(
                recommendation_json.get("backup_confidence_score", 0.0)
            )

            # Extract confidence score
            confidence = float(recommendation_json.get("confidence_score", 70.0))

            # Extract care level
            care_level = recommendation_json.get("care_level", "general_floor")

            # Get the clinical reasoning
            reason = recommendation_json.get(
                "clinical_reasoning", "No specific clinical reasoning provided"
            )

            # Build structured notes from the recommendation
            notes = []

            # Add care level assessment
            care_level_display = {
                "general_floor": "General Pediatric Floor",
                "intermediate_care": "Intermediate Care",
                "picu": "PICU (Pediatric Intensive Care)",
                "nicu": "NICU (Neonatal Intensive Care)",
            }.get(care_level, care_level.upper())

            notes.append(f"Care Level: {care_level_display}")

            # Add backup recommendation information
            notes.append(
                f"\nBackup Recommendation: {backup_campus} (Confidence: {backup_confidence:.1f}%)"
            )

            # Add campus scoring if available
            if (
                "campus_scores" in recommendation_json
                and recommendation_json["campus_scores"]
            ):
                scores = recommendation_json["campus_scores"]
                notes.append("\nCampus Scoring:")

                # Ensure all scores are properly formatted as integers 1-5
                def format_score(score_value):
                    if score_value is None:
                        return "N/A"
                    try:
                        # Handle potential percentage strings by removing % character
                        if isinstance(score_value, str) and "%" in score_value:
                            score_value = score_value.replace("%", "")
                        # Convert to float first, then to int for rounding
                        score_float = float(score_value)
                        # Clamp to 1-5 range
                        return max(1, min(5, int(round(score_float))))
                    except (ValueError, TypeError):
                        return "N/A"

                # Primary campus scores
                if "primary" in scores:
                    primary_scores = scores["primary"]
                    notes.append("\nPrimary Campus Scores:")
                    notes.append(
                        f"- Care Level Match: {format_score(primary_scores.get('care_level_match'))}/5"
                    )
                    notes.append(
                        f"- Specialty Availability: {format_score(primary_scores.get('specialty_availability'))}/5"
                    )
                    notes.append(
                        f"- Capacity: {format_score(primary_scores.get('capacity'))}/5"
                    )
                    notes.append(
                        f"- Location: {format_score(primary_scores.get('location'))}/5"
                    )
                    notes.append(
                        f"- Specific Resources: {format_score(primary_scores.get('specific_resources'))}/5"
                    )

                    # Calculate total score
                    try:
                        individual_scores = [
                            format_score(primary_scores.get("care_level_match")),
                            format_score(primary_scores.get("specialty_availability")),
                            format_score(primary_scores.get("capacity")),
                            format_score(primary_scores.get("location")),
                            format_score(primary_scores.get("specific_resources")),
                        ]
                        if all(isinstance(s, int) for s in individual_scores):
                            total_score = sum(individual_scores)
                            notes.append(f"- Total Primary Score: {total_score}/25")
                    except Exception as e:
                        logger.error(f"Error calculating total score: {str(e)}")

                # Backup campus scores
                if "backup" in scores:
                    backup_scores = scores["backup"]
                    notes.append("\nBackup Campus Scores:")
                    notes.append(
                        f"- Care Level Match: {format_score(backup_scores.get('care_level_match'))}/5"
                    )
                    notes.append(
                        f"- Specialty Availability: {format_score(backup_scores.get('specialty_availability'))}/5"
                    )
                    notes.append(
                        f"- Capacity: {format_score(backup_scores.get('capacity'))}/5"
                    )
                    notes.append(
                        f"- Location: {format_score(backup_scores.get('location'))}/5"
                    )
                    notes.append(
                        f"- Specific Resources: {format_score(backup_scores.get('specific_resources'))}/5"
                    )

                # Calculate total score properly
                total_score = "N/A"
                try:
                    individual_scores = [
                        format_score(scores.get("care_level_match")),
                        format_score(scores.get("specialty_availability")),
                        format_score(scores.get("capacity")),
                        format_score(scores.get("location")),
                        format_score(scores.get("specific_resources")),
                    ]
                    if all(isinstance(s, int) for s in individual_scores):
                        total_score = sum(individual_scores)
                except Exception:
                    pass

                notes.append(f"- Total Score: {total_score}/25")

            # Add specialty services
            if (
                "required_specialties" in recommendation_json
                and recommendation_json["required_specialties"]
            ):
                specialties = recommendation_json["required_specialties"]
                if (
                    specialties
                ):  # Only add this section if there are actually specialties
                    notes.append("\nSpecialty Services Needed:")
                    notes.extend([f"- {service}" for service in specialties])

            # Add exclusion check information
            if (
                "exclusions_checked" in recommendation_json
                and recommendation_json["exclusions_checked"]
            ):
                exclusions = recommendation_json["exclusions_checked"]
                notes.append("\nExclusion Criteria Checked:")

                for exclusion in exclusions:
                    name = exclusion.get("name", "Unknown")
                    found = exclusion.get("found", False)
                    status = "FOUND - REQUIRES HUMAN REVIEW" if found else "Not Found"
                    notes.append(f"- {name}: {status}")

            # Add travel data
            if "addresses" in recommendation_json:
                addresses = recommendation_json["addresses"]
                notes.append("\nLocation Information:")
                if "origin" in addresses:
                    notes.append(f"- Origin Address: {addresses['origin']}")
                if "destination" in addresses:
                    notes.append(f"- Destination Address: {addresses['destination']}")

            # Add ETA information
            if "eta" in recommendation_json:
                eta = recommendation_json["eta"]
                notes.append("\nEstimated Travel:")
                if "minutes" in eta and "transport_mode" in eta:
                    notes.append(
                        f"- ETA: {eta['minutes']} minutes via {eta['transport_mode']}"
                    )

            # Add traffic and weather information
            if "traffic_report" in recommendation_json:
                notes.append(
                    f"- Traffic Conditions: {recommendation_json['traffic_report']}"
                )
            if "weather_report" in recommendation_json:
                notes.append(
                    f"- Weather Conditions: {recommendation_json['weather_report']}"
                )

            # Add bed availability confirmation
            if "bed_availability" in recommendation_json:
                bed_info = recommendation_json["bed_availability"]
                confirmed = bed_info.get("confirmed", False)
                details = bed_info.get("details", "No details provided")
                status = (
                    "Confirmed" if confirmed else "NOT CONFIRMED - CHECK AVAILABILITY"
                )
                notes.append(f"\nBed Availability: {status}")
                notes.append(f"- Details: {details}")

            # Add transport considerations
            if (
                "transport_considerations" in recommendation_json
                and recommendation_json["transport_considerations"]
            ):
                transport = recommendation_json["transport_considerations"]
                notes.append("\nTransport Considerations:")
                if isinstance(transport, list):
                    notes.extend([f"- {item}" for item in transport])
                else:
                    notes.append(f"- {transport}")

            # Add required resources
            if (
                "required_resources" in recommendation_json
                and recommendation_json["required_resources"]
            ):
                resources = recommendation_json["required_resources"]
                notes.append("\nRequired Resources:")
                if isinstance(resources, list):
                    notes.extend([f"- {resource}" for resource in resources])
                else:
                    notes.append(f"- {resources}")

            # Build explainability details
            explainability_details = {}

            # Add care level justification
            explainability_details["care_level"] = care_level_display

            # Add urgency level
            urgency = recommendation_json.get("urgency", "medium")
            explainability_details["urgency"] = urgency

            # Add key factors for recommendation
            key_factors = []
            for key in ["care_level", "confidence_score", "urgency"]:
                if key in recommendation_json:
                    key_factors.append(f"{key}: {recommendation_json[key]}")
            if key_factors:
                explainability_details["key_factors_for_recommendation"] = key_factors

            # Add recommended campus name
            explainability_details["recommended_campus_name"] = campus_name

            # Add excluded campuses with scores and reasons
            if (
                "excluded_campuses" in recommendation_json
                and recommendation_json["excluded_campuses"]
            ):
                excluded_campuses = []
                for campus in recommendation_json["excluded_campuses"]:
                    if (
                        isinstance(campus, dict)
                        and "name" in campus
                        and "reason" in campus
                    ):
                        # Format the total score properly if present
                        formatted_total = None
                        if "total_score" in campus:
                            try:
                                # Handle potential percentage strings by removing % character
                                score_value = campus["total_score"]
                                if isinstance(score_value, str) and "%" in score_value:
                                    score_value = score_value.replace("%", "")
                                # Convert to float or int
                                formatted_total = float(score_value)
                                # If close to integer, convert to int for cleaner display
                                if abs(formatted_total - round(formatted_total)) < 0.01:
                                    formatted_total = int(round(formatted_total))
                            except (ValueError, TypeError):
                                formatted_total = None

                        campus_entry = {
                            "name": campus["name"],
                            "reason": campus["reason"],
                        }

                        # Add formatted score if available
                        if formatted_total is not None:
                            campus_entry["total_score"] = formatted_total

            final_reason = reason

            # Create an enhanced explainability_details dictionary with additional data
            explainability_details = dict(recommendation_json)  # Copy original data

            # Add additional data to explainability details for display
            explainability_details.update(
                {
                    "recommended_campus_name": campus_name,
                    "backup_campus_name": backup_campus,
                    "backup_confidence_score": backup_confidence,
                    "proximity_analysis": {
                        "distance_comparisons": True,  # Flag to indicate distance was considered
                        "closer_options_bypassed": False,  # Will be set to True if a farther campus was chosen
                    },
                }
            )

            # Check if we bypassed a closer option
            if "addresses" in recommendation_json and "eta" in recommendation_json:
                # This is a placeholder - we would need to compare actual distances
                # But we want to ensure the data structure is available
                closer_bypassed = False
                closer_campus = ""
                bypass_reason = ""

                explainability_details["proximity_analysis"].update(
                    {
                        "closer_options_bypassed": closer_bypassed,
                        "closer_campus": closer_campus,
                        "bypass_reason": bypass_reason,
                    }
                )

            # Create and return the recommendation
            return Recommendation(
                transfer_request_id="llm_generated",  # This will be updated by the caller
                recommended_campus_id=campus_name,
                confidence_score=confidence,
                reason=final_reason,
                notes=notes,
                explainability_details=explainability_details,
            )

        except Exception as e:
            logger.error(f"Error processing LLM recommendation: {str(e)}")
            return Recommendation(
                transfer_request_id="error",
                recommended_campus_id="ERROR",
                confidence_score=0.1,
                reason=f"Error processing recommendation: {str(e)}",
                notes=["LLM processing error"],
            )

    def _fallback_recommendation(
        self,
        extracted_entities: Dict[str, Any],
        specialty_assessment: Dict[str, Any],
        exclusion_evaluation: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Fallback recommendation method using rule-based approach.

        Args:
            extracted_entities: Dictionary of extracted clinical entities
            specialty_assessment: Dictionary with specialty need assessment
            exclusion_evaluation: Optional dictionary with exclusion criteria evaluation

        Returns:
            Dictionary with final recommendation
        """
        # Initialize result
        result = {
            "recommendation": {
                "action": "Transfer to most suitable hospital",
                "recommended_campus": None,
                "confidence_score": 70,
                "urgency": "medium",
            },
            "reasoning": "Based on rule-based assessment due to LLM unavailability",
            "considerations": [
                "This is a fallback recommendation",
                "Consider seeking additional clinical input",
            ],
            "clinical_summary": "Limited assessment based on available data",
            "required_resources": [],
            "suggested_followup": "Conduct a detailed clinical review",
        }

        # Get recommended campus from exclusion evaluation if available
        if (
            exclusion_evaluation
            and "recommended_campus" in exclusion_evaluation
            and exclusion_evaluation["recommended_campus"]
        ):
            result["recommendation"]["recommended_campus"] = exclusion_evaluation[
                "recommended_campus"
            ]
            result[
                "reasoning"
            ] += f". Recommended campus: {exclusion_evaluation['recommended_campus']}"

        # Determine urgency based on care level
        care_level = "General"
        if "recommended_care_level" in specialty_assessment:
            care_level = specialty_assessment["recommended_care_level"]

        if care_level in ["ICU", "PICU"]:
            result["recommendation"]["urgency"] = "high"
            result["considerations"].append("Patient requires ICU/PICU level care")
        elif care_level == "NICU":
            result["recommendation"]["urgency"] = "high"
            result["considerations"].append("Patient requires NICU level care")

        # Check for critical vital signs
        if "vital_signs" in extracted_entities:
            vitals = extracted_entities["vital_signs"]
            critical_vitals = []

            if "hr" in vitals:
                try:
                    hr = (
                        int(vitals["hr"])
                        if isinstance(vitals["hr"], (int, str))
                        else None
                    )
                    if hr and (hr > 180 or hr < 60):
                        critical_vitals.append(f"Abnormal HR: {hr}")
                except (ValueError, TypeError):
                    pass

            if "rr" in vitals:
                try:
                    rr = (
                        int(vitals["rr"])
                        if isinstance(vitals["rr"], (int, str))
                        else None
                    )
                    if rr and (rr > 40 or rr < 10):
                        critical_vitals.append(f"Abnormal RR: {rr}")
                except (ValueError, TypeError):
                    pass

            if "bp" in vitals and isinstance(vitals["bp"], str):
                try:
                    systolic = int(vitals["bp"].split("/")[0])
                    if systolic < 80:
                        critical_vitals.append(f"Low BP: {vitals['bp']}")
                except (ValueError, IndexError):
                    pass

            if "o2" in vitals and isinstance(vitals["o2"], str):
                try:
                    o2 = int(vitals["o2"].rstrip("%"))
                    if o2 < 90:
                        critical_vitals.append(f"Low O2: {vitals['o2']}")
                except (ValueError, TypeError):
                    pass

            if critical_vitals:
                result["recommendation"]["urgency"] = "critical"
                result["considerations"].extend(critical_vitals)

        # Build clinical summary
        summary_parts = []

        if "demographics" in extracted_entities:
            demo = extracted_entities["demographics"]
            age_str = f"{demo.get('age', '?')} year-old" if "age" in demo else ""
            gender_str = demo.get("gender", "")
            if age_str or gender_str:
                summary_parts.append(f"{age_str} {gender_str}".strip())

        if (
            "clinical_info" in extracted_entities
            and "chief_complaint" in extracted_entities["clinical_info"]
        ):
            summary_parts.append(
                f"presenting with {extracted_entities['clinical_info']['chief_complaint']}"
            )

        if (
            "required_specialties" in specialty_assessment
            and specialty_assessment["required_specialties"]
        ):
            specialties = [
                s["specialty"] for s in specialty_assessment["required_specialties"][:2]
            ]
            if specialties:
                specialty_str = ", ".join(specialties)
                summary_parts.append(f"requiring {specialty_str}")

        if "recommended_care_level" in specialty_assessment:
            summary_parts.append(
                f"at {specialty_assessment['recommended_care_level']} level of care"
            )

        if summary_parts:
            result["clinical_summary"] = " ".join(summary_parts)

        # Add required resources based on care level
        if care_level == "ICU" or care_level == "PICU":
            result["required_resources"].extend(
                [
                    "ICU/PICU bed",
                    "Critical care transport team",
                    "Continuous monitoring",
                ]
            )
        elif care_level == "NICU":
            result["required_resources"].extend(
                ["NICU bed", "Neonatal transport team", "Continuous monitoring"]
            )
        else:
            result["required_resources"].append("General pediatric bed")

        return result
