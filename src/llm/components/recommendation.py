"""
Recommendation component for LLM integration.

This module handles the generation of final recommendations based on all previous assessments.
"""

import json
import logging
from typing import Dict, Any, List, Optional

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
            # Construct the prompt for recommendation generation
            prompt = self._build_recommendation_prompt(
                extracted_entities, specialty_assessment, exclusion_evaluation
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
                                "description": "The name of the recommended hospital campus"
                            },
                            "care_level": {
                                "type": "string",
                                "enum": ["general_floor", "intermediate_care", "picu", "nicu"],
                                "description": "The minimum appropriate care level needed for this patient"
                            },
                            "confidence_score": {
                                "type": "number",
                                "description": "Confidence score for this recommendation (0-100)"
                            },
                            "clinical_reasoning": {
                                "type": "string",
                                "description": "Clear explanation of why this campus and care level are appropriate (not overrecommending)"
                            },
                            "urgency": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "critical"],
                                "description": "The urgency level for this transfer based on patient stability"
                            },
                            "campus_scores": {
                                "type": "object",
                                "properties": {
                                    "care_level_match": {"type": "number", "description": "Score 1-5 for appropriate care level match"},
                                    "specialty_availability": {"type": "number", "description": "Score 1-5 for needed specialist availability"},
                                    "capacity": {"type": "number", "description": "Score 1-5 for bed availability"},
                                    "location": {"type": "number", "description": "Score 1-5 for proximity to patient's current location"},
                                    "specific_resources": {"type": "number", "description": "Score 1-5 for required equipment/services"}, 
                                    "total_score": {"type": "number", "description": "Sum of all scores (max 25)"}
                                },
                                "required": ["care_level_match", "specialty_availability", "capacity", "location", "specific_resources", "total_score"],
                                "description": "Scoring breakdown for the recommended campus"
                            },
                            "excluded_campuses": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "Name of the excluded campus"
                                        },
                                        "total_score": {
                                            "type": "number",
                                            "description": "Total score for this campus (should be lower than recommended campus)"
                                        },
                                        "reason": {
                                            "type": "string",
                                            "description": "Specific reason why this campus scored lower"
                                        }
                                    },
                                    "required": ["name", "total_score", "reason"]
                                },
                                "description": "Comparative analysis explaining why other campuses were excluded from consideration"
                            },
                            "specialty_services_needed": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of specific specialty services the patient needs at the receiving facility"
                            },
                            "transport_considerations": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Important considerations for the transport team during transfer"
                            },
                            "required_resources": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific resources needed at the receiving facility for this patient"
                            },
                            "clinical_summary": {
                                "type": "string",
                                "description": "Concise summary of the patient's clinical condition and needs"
                            }
                        },
                        "required": ["recommended_campus", "care_level", "confidence_score", "clinical_reasoning", "urgency", "campus_scores", "excluded_campuses"]
                    }
                }
            }
            
            logger.info("Attempting recommendation with JSON schema structure")
            
            # Try using the structured output approach
            try:
                # Call the LLM with JSON schema to enforce structure
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a hospital transfer coordinator providing recommendations in a structured format."}, 
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,  # Keep temperature low for consistency
                    max_tokens=2048,   # Sufficient tokens while keeping reasonable
                    response_format=json_schema
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
                    "\n  \"recommended_campus\": \"Hospital campus name\","
                    "\n  \"care_level\": \"general_floor\" | \"intermediate_care\" | \"picu\" | \"nicu\","
                    "\n  \"confidence_score\": number between 0-100,"
                    "\n  \"clinical_reasoning\": \"Explanation of why this campus and care level are appropriate...\","
                    "\n  \"urgency\": \"low\" | \"medium\" | \"high\" | \"critical\","
                    "\n  \"campus_scores\": {"
                    "\n    \"care_level_match\": number between 1-5,"
                    "\n    \"specialty_availability\": number between 1-5,"
                    "\n    \"capacity\": number between 1-5,"
                    "\n    \"location\": number between 1-5,"
                    "\n    \"specific_resources\": number between 1-5,"
                    "\n    \"total_score\": sum of all scores (max 25)"
                    "\n  },"
                    "\n  \"excluded_campuses\": ["
                    "\n    { \"name\": \"Campus name\", \"total_score\": number, \"reason\": \"Reason why this campus scored lower\" },"
                    "\n    ..."
                    "\n  ],"
                    "\n  \"required_specialties\": [\"specialty1\", \"specialty2\", ...] (empty if no specialists needed),"
                    "\n  \"transport_considerations\": [\"consideration1\", ...],"
                    "\n  \"required_resources\": [\"resource1\", ...],"
                    "\n  \"clinical_summary\": \"Concise summary...\""
                    "\n}"
                    "\n```\n"
                    "Ensure your JSON conforms EXACTLY to this schema and is valid. Remember to only recommend specialty services when truly needed, and to use the minimum appropriate care level."
                )
                
                # Call the LLM with explicit JSON formatting instructions
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a hospital transfer coordinator. Respond ONLY with valid JSON."}, 
                        {"role": "user", "content": prompt + json_instructions}
                    ],
                    temperature=0.1,
                    max_tokens=2048
                )
            
            # Extract response content
            content = response.choices[0].message.content
            logger.debug(f"Raw LLM response (truncated): {content[:500]}...")
            
            # Check for response truncation
            finish_reason = response.choices[0].finish_reason
            if finish_reason == "length":
                logger.warning(f"LLM response was truncated (finish_reason={finish_reason})")
            elif finish_reason != "stop":
                logger.warning(f"Unexpected finish reason: {finish_reason}")
            
            # Parse the response - may contain JSON but with content outside JSON blocks
            try:
                # First try direct parsing
                try:
                    recommendation_json = json.loads(content)
                    logger.info("Successfully parsed structured recommendation response directly")
                except json.JSONDecodeError:
                    # Use our robust parser for more complex responses
                    logger.info("Direct parsing failed, using robust parser")
                    recommendation_json = robust_json_parser(content)
                    if not recommendation_json:
                        logger.error("Robust JSON parsing also failed")
                        raise ValueError("Failed to parse LLM response as JSON")
                    logger.info("Successfully parsed JSON with robust parser")
                
                # Log the parsed structure
                logger.info(f"Parsed recommendation response, keys: {list(recommendation_json.keys())}")
                
                # Some models might still wrap the output, so handle that case
                if "recommendation" not in recommendation_json and isinstance(recommendation_json, dict):
                    # Some models might return a wrapper object when using schemas
                    for key, value in recommendation_json.items():
                        if isinstance(value, dict) and "recommendation" in value:
                            logger.info(f"Found recommendation in nested field '{key}'")
                            recommendation_json = value
                            break
                
                # Convert the JSON response to a Recommendation object
                recommendation_obj = self._convert_to_recommendation(recommendation_json)
                return recommendation_obj
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed despite schema: {str(e)}")
                logger.warning("Falling back to robust parser")
                recommendation_json = robust_json_parser(content)
                
                if recommendation_json and "recommendation" in recommendation_json:
                    # Convert the JSON response to a Recommendation object
                    recommendation_obj = self._convert_to_recommendation(recommendation_json)
                    return recommendation_obj
                else:
                    logger.error("Failed to generate a valid recommendation with schema")
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
        essential_patient_info = self._extract_essential_patient_info(extracted_entities)
        essential_specialty_info = self._extract_essential_specialty_info(specialty_assessment)
        essential_exclusion_info = self._extract_essential_exclusion_info(exclusion_evaluation)
        
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
                    "Capacity": "Largest bed capacity in the system"
                }
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
                    "Capacity": "Medium capacity"
                }
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
                    "Capacity": "Medium capacity"
                }
            },
            {
                "name": "Texas Children's Hospital - North Austin Campus",
                "capabilities": {
                    "PICU": "Standard pediatric intensive care services",
                    "NICU": "Level III",
                    "Trauma": "Level III Pediatric Trauma Center",
                    "Specialists": "Limited specialty coverage",
                    "Surgery": "Basic pediatric surgery",
                    "Capacity": "Smaller capacity"
                }
            },
            {
                "name": "Texas Children's Hospital - Pavilion for Women",
                "capabilities": {
                    "NICU": "Level IV",
                    "Specialists": "Maternal-fetal medicine specialists",
                    "Surgery": "Neonatal surgery",
                    "Capacity": "Specialized for maternal and neonatal care only"
                }
            }
        ]
        
        # Convert to string representation
        hospitals_str = "Available Hospital Campuses:\n"
        for hospital in hospitals:
            hospitals_str += f"\n{hospital['name']}:\n"
            for capability, level in hospital['capabilities'].items():
                hospitals_str += f"  - {capability}: {level}\n"
        
        return f"""
You are a medical transfer coordinator tasked with recommending a hospital campus for pediatric patient transfer. Your job is to match patients with the appropriate level of care - not every patient needs the highest level of care or specialists.

## PATIENT INFORMATION
{essential_patient_info}

## SPECIALTY NEEDS
{essential_specialty_info}

## EXCLUSION CRITERIA
{essential_exclusion_info}

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

3. PICU (Pediatric Intensive Care):
   - Respiratory failure requiring ventilator or high-flow oxygen
   - Hemodynamic instability requiring vasopressors
   - Severe neurological compromise
   - Multiple organ system involvement requiring intensive monitoring
   - Post-major surgery requiring intensive monitoring

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
Score each campus on a scale of 1-5 for this specific patient:
1. CARE LEVEL MATCH: Does the campus provide the appropriate level of care? (Not higher than needed)
2. SPECIALTY AVAILABILITY: Are needed specialists available? (If specialists not needed, all campuses score 5)
3. CAPACITY: Consider bed availability
4. LOCATION: Proximity to patient's current location
5. SPECIFIC RESOURCES: Special equipment or services required

Follow this critical reasoning chain in detail:
1. First analyze the patient's condition and determine MINIMUM appropriate care level needed
2. Identify if specialists are truly required (not just potentially helpful)
3. Score each campus using the criteria above
4. Recommend the campus with the highest total score
5. Explain why other campuses scored lower
6. Assign an appropriate urgency level (low, medium, high, critical) based on patient stability

Your recommendation must include:
- A specific recommended hospital campus from the list above
- Clear explanation of the minimum appropriate care level needed (avoid recommending higher levels than necessary)
- The score breakdown for the recommended campus
- Comparative analysis explaining why other campuses were excluded
- Only recommend specialty services that are truly required
- Important considerations for the transport team
- Essential resources needed (not an exhaustive list of all possible resources)

This recommendation will directly inform critical patient transfer decisions.
"""
    
    def _extract_essential_patient_info(self, entities: Dict[str, Any]) -> str:
        """Extract the most relevant patient information in a concise format."""
        if not entities:
            return "No patient information available"
            
        # Extract demographics
        demographics = entities.get('demographics', {})
        age = demographics.get('age', '?')
        gender = demographics.get('gender', '?')
        
        # Extract clinical info
        clinical_info = entities.get('clinical_info', {})
        chief_complaint = clinical_info.get('chief_complaint', 'No chief complaint')
        
        # Extract vital signs if available
        vitals = entities.get('vital_signs', {})
        vital_str = ""
        if vitals:
            vital_items = []
            for k, v in vitals.items():
                if v is not None:
                    vital_items.append(f"{k}: {v}")
            if vital_items:
                vital_str = "\nVitals: " + ", ".join(vital_items)
        
        # Extract diagnoses
        diagnoses = entities.get('diagnoses', [])
        diagnosis_str = "\nDiagnoses: " + ", ".join(diagnoses) if diagnoses else ""
        
        # Combine into concise summary
        return f"{age} y.o. {gender}, {chief_complaint}{vital_str}{diagnosis_str}"
    
    def _extract_essential_specialty_info(self, assessment: Dict[str, Any]) -> str:
        """Extract the most relevant specialty assessment information."""
        if not assessment:
            return "No specialty assessment available"
            
        # Extract recommended care level
        care_level = assessment.get('recommended_care_level', 'Unknown')
        
        # Extract required specialties
        specialties = []
        for spec in assessment.get('required_specialties', []):
            if isinstance(spec, dict) and 'specialty' in spec:
                importance = spec.get('importance', '')
                specialties.append(f"{spec['specialty']} ({importance})" if importance else spec['specialty'])
        
        specialty_str = "\nSpecialties: " + ", ".join(specialties) if specialties else ""
        
        # Extract potential conditions
        conditions = assessment.get('potential_conditions', [])
        condition_str = "\nConditions: " + ", ".join(conditions) if conditions else ""
        
        return f"Care Level: {care_level}{specialty_str}{condition_str}"
    
    def _extract_essential_exclusion_info(self, exclusion: Optional[Dict[str, Any]]) -> str:
        """Extract essential exclusion information."""
        if not exclusion:
            return "No exclusion criteria applied"
            
        # Check if there are any exclusions
        excluded_campuses = exclusion.get('excluded_campuses', [])
        if not excluded_campuses:
            return "No campuses excluded"
            
        # Format exclusion reasons concisely
        exclusion_reasons = []
        for campus in excluded_campuses:
            name = campus.get('campus_name', '?')
            reason = campus.get('reason', 'unknown reason')
            exclusion_reasons.append(f"{name}: {reason}")
            
        return "\n".join(exclusion_reasons)

    def _convert_to_recommendation(self, recommendation_json: Dict[str, Any]) -> Recommendation:
        """
        Convert the LLM recommendation JSON response to a Recommendation object.
        
        Args:
            recommendation_json: The parsed JSON response from the LLM
            
        Returns:
            Recommendation object with the appropriate fields populated
        """
        try:
            logger.info(f"Processing LLM recommendation: {json.dumps(recommendation_json, indent=2)[:1000]}...")
            
            # Extract campus name
            campus_name = recommendation_json.get("recommended_campus", "No specific campus recommended")
            
            # Extract confidence score
            confidence = float(recommendation_json.get("confidence_score", 70.0))
            
            # Extract care level
            care_level = recommendation_json.get("care_level", "general_floor")
            
            # Get the clinical reasoning
            reason = recommendation_json.get("clinical_reasoning", "No specific clinical reasoning provided")
            
            # Build structured notes from the recommendation
            notes = []
            
            # Add care level assessment
            care_level_display = {
                "general_floor": "General Pediatric Floor",
                "intermediate_care": "Intermediate Care",
                "picu": "PICU (Pediatric Intensive Care)",
                "nicu": "NICU (Neonatal Intensive Care)"
            }.get(care_level, care_level.upper())
            
            notes.append(f"Care Level: {care_level_display}")
            
            # Add campus scoring if available
            if "campus_scores" in recommendation_json and recommendation_json["campus_scores"]:
                scores = recommendation_json["campus_scores"]
                notes.append("\nCampus Scoring:")
                
                # Ensure all scores are properly formatted as integers 1-5
                def format_score(score_value):
                    if score_value is None:
                        return 'N/A'
                    try:
                        # Handle potential percentage strings by removing % character
                        if isinstance(score_value, str) and '%' in score_value:
                            score_value = score_value.replace('%', '')
                        # Convert to float first, then to int for rounding
                        score_float = float(score_value)
                        # Clamp to 1-5 range
                        return max(1, min(5, int(round(score_float))))
                    except (ValueError, TypeError):
                        return 'N/A'
                
                # Format individual scores
                notes.append(f"- Care Level Match: {format_score(scores.get('care_level_match'))}/5")
                notes.append(f"- Specialty Availability: {format_score(scores.get('specialty_availability'))}/5")
                notes.append(f"- Capacity: {format_score(scores.get('capacity'))}/5")
                notes.append(f"- Location: {format_score(scores.get('location'))}/5")
                notes.append(f"- Specific Resources: {format_score(scores.get('specific_resources'))}/5")
                
                # Calculate total score properly
                total_score = 'N/A'
                try:
                    individual_scores = [
                        format_score(scores.get('care_level_match')),
                        format_score(scores.get('specialty_availability')),
                        format_score(scores.get('capacity')),
                        format_score(scores.get('location')),
                        format_score(scores.get('specific_resources'))
                    ]
                    if all(isinstance(s, int) for s in individual_scores):
                        total_score = sum(individual_scores)
                except Exception:
                    pass
                
                notes.append(f"- Total Score: {total_score}/25")
            
            # Add specialty services
            if "required_specialties" in recommendation_json and recommendation_json["required_specialties"]:
                specialties = recommendation_json["required_specialties"]
                if specialties:  # Only add this section if there are actually specialties
                    notes.append("\nSpecialty Services Needed:")
                    notes.extend([f"- {service}" for service in specialties])
                
            # Add transport considerations
            if "transport_considerations" in recommendation_json and recommendation_json["transport_considerations"]:
                transport = recommendation_json["transport_considerations"]
                notes.append("\nTransport Considerations:")
                if isinstance(transport, list):
                    notes.extend([f"- {item}" for item in transport])
                else:
                    notes.append(f"- {transport}")
                
            # Add required resources
            if "required_resources" in recommendation_json and recommendation_json["required_resources"]:
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
            if "excluded_campuses" in recommendation_json and recommendation_json["excluded_campuses"]:
                excluded_campuses = []
                for campus in recommendation_json["excluded_campuses"]:
                    if isinstance(campus, dict) and "name" in campus and "reason" in campus:
                        # Format the total score properly if present
                        formatted_total = None
                        if "total_score" in campus:
                            try:
                                # Handle potential percentage strings by removing % character
                                score_value = campus["total_score"]
                                if isinstance(score_value, str) and '%' in score_value:
                                    score_value = score_value.replace('%', '')
                                # Convert to float or int
                                formatted_total = float(score_value)
                                # If close to integer, convert to int for cleaner display
                                if abs(formatted_total - round(formatted_total)) < 0.01:
                                    formatted_total = int(round(formatted_total))
                            except (ValueError, TypeError):
                                formatted_total = None
                        
                        campus_entry = {
                            "name": campus["name"],
                            "reason": campus["reason"]
                        }
                        
                        # Add formatted score if available
                        if formatted_total is not None:
                            campus_entry["total_score"] = formatted_total
                            
                        excluded_campuses.append(campus_entry)
                        
                if excluded_campuses:
                    explainability_details["excluded_campuses"] = excluded_campuses
            
            # Create and return the recommendation object
            return Recommendation(
                transfer_request_id="LLM_GENERATED",
                recommended_campus_id=campus_name,  # Use the actual campus name as ID
                confidence_score=confidence,
                reason=reason,
                notes=notes,
                explainability_details=explainability_details
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
                "urgency": "medium"
            },
            "reasoning": "Based on rule-based assessment due to LLM unavailability",
            "considerations": [
                "This is a fallback recommendation",
                "Consider seeking additional clinical input"
            ],
            "clinical_summary": "Limited assessment based on available data",
            "required_resources": [],
            "suggested_followup": "Conduct a detailed clinical review"
        }
        
        # Get recommended campus from exclusion evaluation if available
        if (exclusion_evaluation and 
            "recommended_campus" in exclusion_evaluation and 
            exclusion_evaluation["recommended_campus"]):
            result["recommendation"]["recommended_campus"] = exclusion_evaluation["recommended_campus"]
            result["reasoning"] += f". Recommended campus: {exclusion_evaluation['recommended_campus']}"
        
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
                    hr = int(vitals["hr"]) if isinstance(vitals["hr"], (int, str)) else None
                    if hr and (hr > 180 or hr < 60):
                        critical_vitals.append(f"Abnormal HR: {hr}")
                except (ValueError, TypeError):
                    pass
            
            if "rr" in vitals:
                try:
                    rr = int(vitals["rr"]) if isinstance(vitals["rr"], (int, str)) else None
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
            gender_str = demo.get('gender', '')
            if age_str or gender_str:
                summary_parts.append(f"{age_str} {gender_str}".strip())
        
        if "clinical_info" in extracted_entities and "chief_complaint" in extracted_entities["clinical_info"]:
            summary_parts.append(f"presenting with {extracted_entities['clinical_info']['chief_complaint']}")
        
        if "required_specialties" in specialty_assessment and specialty_assessment["required_specialties"]:
            specialties = [s["specialty"] for s in specialty_assessment["required_specialties"][:2]]
            if specialties:
                specialty_str = ", ".join(specialties)
                summary_parts.append(f"requiring {specialty_str}")
        
        if "recommended_care_level" in specialty_assessment:
            summary_parts.append(f"at {specialty_assessment['recommended_care_level']} level of care")
        
        if summary_parts:
            result["clinical_summary"] = " ".join(summary_parts)
        
        # Add required resources based on care level
        if care_level == "ICU" or care_level == "PICU":
            result["required_resources"].extend([
                "ICU/PICU bed",
                "Critical care transport team",
                "Continuous monitoring"
            ])
        elif care_level == "NICU":
            result["required_resources"].extend([
                "NICU bed",
                "Neonatal transport team",
                "Continuous monitoring"
            ])
        else:
            result["required_resources"].append("General pediatric bed")
        
        return result
