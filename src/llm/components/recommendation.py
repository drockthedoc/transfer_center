"""Recommendation component for LLM integration.

This module handles the generation of final recommendations based on all previous assessments.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Import the LLM logger
from src.llm.llm_logging import get_llm_logger

from src.core.models import Recommendation, Location  # Added import
from src.core.decision_bakup.confidence_estimator import calculate_recommendation_confidence
from src.llm.utils import robust_json_parser
from src.utils.geolocation import calculate_distance  # Added import

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
        available_hospitals: Optional[List[Dict[str, Any]]] = None,
        census_data: Optional[Dict[str, Any]] = None,
    ) -> Recommendation:
        """Generate final recommendation based on previous steps.

        Args:
            extracted_entities: Dictionary of extracted clinical entities
            specialty_assessment: Dictionary with specialty need assessment
            exclusion_evaluation: Optional dictionary with exclusion criteria evaluation

        Returns:
            Dictionary with final recommendation
        """
        logger.info("===============================================================")
        logger.info("============== BEGINNING RECOMMENDATION GENERATION =============")
        logger.info("===============================================================")
        
        # Log input data details
        logger.info(f"Input extracted_entities type: {type(extracted_entities)}")
        if extracted_entities:
            logger.info(f"Input extracted_entities keys: {list(extracted_entities.keys())}")
            for key in extracted_entities.keys():
                if isinstance(extracted_entities[key], dict):
                    logger.info(f"  - '{key}' contains: {list(extracted_entities[key].keys())}")
        else:
            logger.error("No extracted_entities provided!")
            
        logger.info(f"Input specialty_assessment type: {type(specialty_assessment)}")
        if specialty_assessment:
            logger.info(f"Input specialty_assessment keys: {list(specialty_assessment.keys())}")
        else:
            logger.error("No specialty_assessment provided!")
            
        logger.info(f"Input exclusion_evaluation type: {type(exclusion_evaluation) if exclusion_evaluation else 'None'}")
        if exclusion_evaluation:
            logger.info(f"Input exclusion_evaluation keys: {list(exclusion_evaluation.keys())}")
        else:
            logger.warning("No exclusion_evaluation provided - using null value")
        
        # Print to console for debugging
        print("============================================")
        print("BEGINNING RECOMMENDATION GENERATION PROCESS")
        print(f"Entities: {list(extracted_entities.keys()) if extracted_entities else 'None'}")
        print(f"Specialties: {list(specialty_assessment.keys()) if specialty_assessment else 'None'}")
        print(f"Exclusions: {list(exclusion_evaluation.keys()) if exclusion_evaluation else 'None'}")

        # First try with the LLM approach
        logger.info("Attempting LLM recommendation generation")
        
        # Log available hospital data
        if available_hospitals:
            logger.info(f"Using {len(available_hospitals)} hospitals for recommendation")
            # Log hospital names for debugging
            hospital_names = [h.name if h and hasattr(h, 'name') else 'Unknown Hospital' for h in available_hospitals]
            logger.info(f"Available hospitals: {hospital_names}")
        else:
            logger.warning("No available hospitals provided - recommendation may be inaccurate")
            
        # Log census data if available
        if census_data:
            logger.info("Using census data for recommendation")
            if isinstance(census_data, dict):
                logger.info(f"Census data keys: {list(census_data.keys())}")
        
        # Call LLM recommendation with all available data
        llm_result = self._try_llm_recommendation(
            extracted_entities, 
            specialty_assessment, 
            exclusion_evaluation,
            available_hospitals,
            census_data
        )

        # Always return the LLM recommendation if it's available - no fallback to rule-based
        if llm_result:
            logger.info("LLM recommendation generation succeeded")
            logger.info(f"Final recommendation type: {type(llm_result)}")
            if hasattr(llm_result, 'recommended_campus_id'):
                logger.info(f"Final recommended campus: {llm_result.recommended_campus_id}")
                logger.info(f"Final confidence score: {llm_result.confidence_score}")
                logger.info(f"Reason length: {len(llm_result.reason) if llm_result.reason else 0}")
            else:
                logger.error(f"Recommendation missing expected attributes: {dir(llm_result)[:10]}")
                
            # Print the final recommendation
            print(f"LLM recommendation completed successfully")
            print(f"Campus: {llm_result.recommended_campus_id if hasattr(llm_result, 'recommended_campus_id') else 'Unknown'}")
            print(f"Confidence: {llm_result.confidence_score if hasattr(llm_result, 'confidence_score') else 'Unknown'}")
            
            logger.info("===============================================================")
            logger.info("============== RECOMMENDATION GENERATION COMPLETE ==============")
            logger.info("===============================================================")
            return llm_result

        # If LLM approach fails completely, log the error and return a basic error recommendation
        logger.error("LLM recommendation generation failed completely")
        logger.error("No recommendation was generated - will return error recommendation")
        print("ERROR: LLM recommendation generation failed completely")
        
        # Create a basic error recommendation with a low confidence score
        recommendation_data = {
            "patient_demographics": extracted_entities.get("demographics", {}),
            "clinical_history": "",
            "chief_complaint": "",
            "extracted_vital_signs": {}
        }
        
        # Calculate a minimal confidence score based on very limited data
        confidence = calculate_recommendation_confidence(recommendation_data) / 2  # Halve it due to error condition
        
        return Recommendation(
            transfer_request_id="error",
            recommended_campus_id="ERROR",
            confidence_score=confidence,  # Using calculated low confidence
            reason="Failed to generate a recommendation with the LLM",
            notes=["LLM error - please check the logs and try again"],
            explainability_details=recommendation_data
        )

    def _try_llm_recommendation(
        self,
        extracted_entities: Dict[str, Any],
        specialty_assessment: Dict[str, Any],
        exclusion_evaluation: Optional[Dict[str, Any]] = None,
        available_hospitals: Optional[List[Dict[str, Any]]] = None,
        census_data: Optional[Dict[str, Any]] = None,
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
            # Build the prompt for the LLM with all available context
            prompt, has_scores, score_count = self._build_recommendation_prompt(
                extracted_entities, 
                specialty_assessment, 
                exclusion_evaluation,
                available_hospitals,
                census_data
            )
            
            # Add JSON instructions
            json_instructions = """
Use the above information to provide a hospital transfer recommendation in the following JSON format:
```json
{
  "recommended_campus_id": string,    // The ID of the recommended hospital campus
  "recommended_campus_name": string,  // The name of the recommended hospital campus
  "care_level": string,               // Recommended care level (e.g., General, ICU, PICU)
  "confidence_score": number,         // Confidence score (0-100) for this recommendation
  "explainability_details": {
    "main_recommendation_reason": string, // Primary reason for choosing this specific campus
    "alternative_reasons": {        // Optional: Reasons for NOT choosing other considered campuses. Key is campus_id or name.
      "OtherCampusID1": "Reason why OtherCampusID1 was not chosen...",
      "OtherCampusName2": "Reason why OtherCampusName2 was not chosen..."
    },
    "key_factors_considered": [string], // List of key factors, e.g., ["distance", "specialty_match", "bed_availability_heuristic"]
    "confidence_explanation": string    // Optional: Brief explanation of the confidence score
  },
  "notes": [string],                  // Optional: Any additional notes or brief details
  "transport_details": {              // Details about transport for the UI
    "mode": string,                   // Suggested transport mode (e.g., "GROUND_AMBULANCE", "HELICOPTER")
    "estimated_time_minutes": number, // Estimated transport time in minutes
    "special_requirements": string    // Any special transport requirements (e.g., "Requires NICU-capable team")
  },
  "conditions": {                     // Current conditions affecting transport for the UI
    "weather": string,                // Brief weather summary (e.g., "Clear, 75F")
    "traffic": string                 // Brief traffic summary (e.g., "Light traffic on I-10")
  }
}
```

**Instructions for Explainability Details:**
- `main_recommendation_reason`: Clearly state why the *recommended_campus_id* is the best choice.
- `alternative_reasons`: If other campuses were strong contenders but ultimately not chosen, briefly explain why for each. Use their ID or name as the key.
- `key_factors_considered`: List the critical factors that influenced the decision (e.g., specific patient need, unique hospital capability, distance, bed availability).
- `confidence_explanation`: Briefly explain why the confidence score is what it is (e.g., "High confidence due to clear specialty match and bed availability" or "Moderate confidence due to conflicting factors").

Do not include any text before or after the JSON. Only return a valid JSON object.
"""
            
            # Call the LLM with extensive logging
            logger.info(f"========== SENDING RECOMMENDATION PROMPT TO {self.model} ===========")
            logger.debug(f"FULL RECOMMENDATION PROMPT:\n{prompt + json_instructions}")
            
            # Print to console for debugging
            print(f"===== SENDING RECOMMENDATION PROMPT =====")
            print(f"Prompt length: {len(prompt + json_instructions)} characters")
            print(f"JSON schema included: {len(json_instructions)} characters")
            
            # Get the LLM logger
            llm_logger = get_llm_logger()
            
            # Prepare messages for the API call
            messages = [
                {
                    "role": "system",
                    "content": "You are a hospital transfer coordinator. Respond ONLY with valid JSON.",
                },
                {"role": "user", "content": prompt + json_instructions},
            ]
            
            # Log the prompt BEFORE sending it (pre-call logging)
            llm_logger.log_prompt(
                component="RecommendationGenerator",
                method="_try_llm_recommendation",
                prompt=prompt + json_instructions,
                model=self.model,
                messages=messages,
                metadata={
                    "extracted_entities_keys": list(extracted_entities.keys()) if extracted_entities else [],
                    "specialty_assessment_keys": list(specialty_assessment.keys()) if specialty_assessment else [],
                    "exclusion_evaluation_keys": list(exclusion_evaluation.keys()) if exclusion_evaluation else [],
                    "has_scores": has_scores,
                    "score_count": score_count
                }
            )
            
            # Call the API with the combined prompt
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=2048,
            )

            # Extract response content with comprehensive logging
            content = response.choices[0].message.content
            
            # IMMEDIATELY log the raw response BEFORE any processing
            with open('/Users/derek/CascadeProjects/transfer_center/logs/llm_raw_responses.log', 'a') as raw_log:
                raw_log.write(f"\n\n=== RAW LLM RESPONSE {datetime.now()} ===\n")
                raw_log.write(f"MODEL: {self.model}\n")
                raw_log.write(f"COMPONENT: RecommendationGenerator._try_llm_recommendation\n")
                raw_log.write(f"CONTENT:\n{content}\n")
                raw_log.write("=== END OF RESPONSE ===\n")
            
            # Log using both standard logging and the LLM logger
            logger.info(f"========== RAW LLM RESPONSE RECEIVED ===========")
            logger.info(f"FULL RAW RESPONSE:\n{content}")
            
            # Log the complete interaction with the LLM logger
            llm_logger.log_interaction(
                component="RecommendationGenerator",
                method="_try_llm_recommendation",
                input_data={
                    "prompt": prompt,
                    "json_instructions": json_instructions,
                    "messages": messages
                },
                output_data=content,
                model=self.model,
                success=True,
                metadata={
                    "token_usage": response.usage.total_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "finish_reason": response.choices[0].finish_reason
                }
            )
            
            # Print detailed debugging info to console
            print(f"===== LLM RESPONSE RECEIVED =====\nLength: {len(content)}")
            print(f"Response preview: {content[:100]}...")
            print(f"Response token usage: {response.usage.total_tokens} tokens total")
            print(f"Prompt tokens: {response.usage.prompt_tokens}, Completion tokens: {response.usage.completion_tokens}")

            # Check for response truncation
            finish_reason = response.choices[0].finish_reason
            if finish_reason == "length":
                logger.warning(f"LLM response was truncated (finish_reason={finish_reason})")

            # Try to parse the JSON response with extensive logging at every step
            logger.info("========== BEGINNING JSON PARSING PROCESS ===========")
            try:
                # First try to use the robust_json_parser
                logger.info("Attempting to parse with robust_json_parser")
                def strip_markdown_code_blocks(text):
                    """Strip markdown code block delimiters from the text."""
                    # Check if the text starts with a code block marker
                    if text.strip().startswith('```'):
                        # Remove opening code block (```json or just ```) and language specifier
                        text = re.sub(r'^\s*```(?:json|javascript|python)?\s*\n', '', text)
                        # Remove closing code block
                        text = re.sub(r'\n\s*```\s*$', '', text)
                    return text.strip()
                    
                try:
                    # Call the function directly (not as a method)
                    print(f"PARSE ATTEMPT 1: Using robust_json_parser function")
                    
                    # Clean the response of markdown code blocks
                    original_content = content
                    content = strip_markdown_code_blocks(content)
                    
                    # Log what we're about to parse
                    logger.info(f"ORIGINAL CONTENT (before stripping):\n{original_content[:500]}{'...' if len(original_content) > 500 else ''}")
                    logger.info(f"CLEANED CONTENT (after stripping):\n{content[:500]}{'...' if len(content) > 500 else ''}")
                    
                    # If content changed, we had markdown blocks
                    if content != original_content:
                        logger.info("Detected and removed markdown code blocks from LLM response")
                        print("Detected and removed markdown code blocks from LLM response")
                    
                    # Try to parse the raw response
                    recommendation_json = robust_json_parser(content)
                    
                    # Log successful parsing in great detail
                    logger.info(f"robust_json_parser SUCCESS")
                    logger.info(f"Parsed JSON type: {type(recommendation_json)}")
                    
                    # Raw debug log for EXACTLY what was parsed
                    with open('/Users/derek/CascadeProjects/transfer_center/logs/json_parsing.log', 'a') as json_log:
                        json_log.write(f"\n\n=== PARSED JSON OBJECT {datetime.now()} ===\n")
                        json_log.write(f"TYPE: {type(recommendation_json)}\n")
                        json_log.write(f"REPR: {repr(recommendation_json)}\n")
                        try:
                            json_log.write(f"JSON DUMP: {json.dumps(recommendation_json, indent=2, default=str)}\n")
                        except Exception as dump_error:
                            json_log.write(f"ERROR DUMPING: {dump_error}\n")
                        json_log.write("=== END OF PARSED JSON ===\n")
                    
                    # Add detailed error handling for different return types
                    if isinstance(recommendation_json, list):
                        error_msg = f"ERROR: LLM returned a LIST instead of a DICT! List content: {recommendation_json}"
                        logger.error(error_msg)
                        print(f"ERROR: LLM returned a list with {len(recommendation_json)} items instead of a dictionary")
                        
                        # Log to LLM logger
                        get_llm_logger().log_interaction(
                            component="RecommendationGenerator",
                            method="_parse_json",
                            input_data=content,
                            output_data=recommendation_json,
                            model=self.model,
                            success=False,
                            error=error_msg
                        )
                        
                        # Try to convert a list with a single dictionary item to just that dictionary
                        if len(recommendation_json) == 1 and isinstance(recommendation_json[0], dict):
                            logger.info("Attempting to recover by extracting the first item from the list")
                            recommendation_json = recommendation_json[0]
                            logger.info(f"Recovered dictionary with keys: {list(recommendation_json.keys())}")
                        else:
                            logger.error("Cannot convert list to dictionary - will cause 'items' attribute error")
                            # Fallback to an empty dictionary to prevent the items attribute error
                            recommendation_json = {
                                "recommended_campus": "ERROR",
                                "care_level": "unknown",
                                "confidence_score": 0,
                                "clinical_reasoning": f"Error: LLM returned a list instead of a dictionary with {len(recommendation_json)} items"
                            }
                            logger.info(f"Created fallback dictionary: {recommendation_json}")
                    elif isinstance(recommendation_json, dict):
                        logger.info(f"Parsed JSON keys: {list(recommendation_json.keys())}")
                    else:
                        logger.info(f"Parsed JSON is not a dict or list but {type(recommendation_json)}")
                        print(f"WARNING: LLM returned an unexpected type: {type(recommendation_json)}")
                        # Fallback to an empty dictionary
                        recommendation_json = {
                            "recommended_campus": "ERROR",
                            "care_level": "unknown",
                            "confidence_score": 0,
                            "clinical_reasoning": f"Error: LLM returned unexpected type {type(recommendation_json)}"
                        }

                    
                    print(f"===== JSON PARSING SUCCEEDED =====\nKeys: {list(recommendation_json.keys()) if isinstance(recommendation_json, dict) else 'Not a dict'}")
                    logger.info(f"COMPLETE PARSED JSON:\n{json.dumps(recommendation_json, indent=2)}")
                    
                except Exception as parser_error:
                    # Log parsing failure in extreme detail
                    error_msg = f"robust_json_parser FAILED: {str(parser_error)}"
                    logger.error(error_msg)
                    logger.error(f"Parser error type: {type(parser_error).__name__}")
                    
                    # Record the exact raw content that failed parsing
                    with open('/Users/derek/CascadeProjects/transfer_center/logs/json_parsing_errors.log', 'a') as err_log:
                        err_log.write(f"\n\n=== JSON PARSING ERROR {datetime.now()} ===\n")
                        err_log.write(f"ERROR: {error_msg}\n")
                        err_log.write(f"CONTENT THAT FAILED PARSING:\n{content}\n")
                        err_log.write("=== END OF ERROR REPORT ===\n")
                    
                    # Log to LLM logger
                    get_llm_logger().log_interaction(
                        component="RecommendationGenerator",
                        method="_parse_json_error",
                        input_data=content,
                        output_data=None,
                        model=self.model,
                        success=False,
                        error=error_msg
                    )
                    logger.error(f"Error type: {type(parser_error).__name__}")
                    print(f"===== JSON PARSING FAILED =====\n{str(parser_error)}\nRaw response content: {content[:100]}...")
                    
                    # Try manual extraction methods with detailed logging
                    if "```json" in content and "```" in content.split("```json", 1)[1]:
                        logger.info("Attempting code block extraction")
                        print("PARSE ATTEMPT 2: Extracting from code block")
                        # Extract JSON from code block
                        json_content = content.split("```json", 1)[1].split("```", 1)[0].strip()
                        logger.debug(f"Extracted code block:\n{json_content}")
                        
                        try:
                            recommendation_json = json.loads(json_content)
                            logger.info("Code block JSON parsing SUCCESS")
                            logger.info(f"Parsed JSON keys: {list(recommendation_json.keys()) if isinstance(recommendation_json, dict) else 'Not a dict'}")
                            logger.info(f"COMPLETE PARSED JSON FROM CODE BLOCK:\n{json.dumps(recommendation_json, indent=2)}")
                        except json.JSONDecodeError as json_error:
                            logger.error(f"Code block parsing FAILED: {str(json_error)}")
                            logger.error(f"Invalid JSON from code block: {json_content[:100]}...")
                            
                            # Fall back to direct JSON parsing
                            logger.info("Attempting direct parsing of full response")
                            print("PARSE ATTEMPT 3: Direct parsing of full response")
                            try:
                                recommendation_json = json.loads(content)
                                logger.info("Direct parsing SUCCESS")
                                logger.info(f"Parsed JSON keys: {list(recommendation_json.keys()) if isinstance(recommendation_json, dict) else 'Not a dict'}")
                            except json.JSONDecodeError as full_error:
                                logger.error(f"Direct parsing FAILED: {str(full_error)}")
                                logger.error("All JSON parsing methods failed")
                                logger.error(f"UNPARSEABLE CONTENT:\n{content}")
                                return None
                    else:
                        # Try direct JSON parsing
                        logger.info("No code block found, attempting direct parsing")
                        print("PARSE ATTEMPT 2: Direct parsing of full response")
                        try:
                            recommendation_json = json.loads(content)
                            logger.info("Direct parsing SUCCESS")
                            logger.info(f"Parsed JSON keys: {list(recommendation_json.keys()) if isinstance(recommendation_json, dict) else 'Not a dict'}")
                        except json.JSONDecodeError as direct_error:
                            line_number = content[:direct_error.pos].count('\n') + 1
                            logger.error(f"Direct parsing FAILED: {str(direct_error)}")
                            logger.error(f"Error position: character {direct_error.pos}, line {line_number}")
                            logger.error(f"Context around error: '{content[max(0, direct_error.pos-20):direct_error.pos+20]}'")
                            logger.error("All JSON parsing methods failed")
                            logger.error(f"UNPARSEABLE CONTENT:\n{content}")
                            return None

                # Log the final parsed structure
                logger.info("========== JSON PARSING COMPLETE ===========")
                logger.info(f"Successfully parsed recommendation JSON with {len(recommendation_json.keys()) if isinstance(recommendation_json, dict) else 0} keys")
                
                # Validate that the LLM used the pediatric scores in its decision-making
                if has_scores and recommendation_json:
                    # Look for score references in reasoning or justification
                    score_references = 0
                    score_terms = ["pews", "trap", "prism", "cameo", "queensland", "chews", "tps", 
                                   "score", "scoring", "pediatric score", "severity score"]
                    
                    # Check various fields for score references
                    fields_to_check = [
                        "clinical_reasoning", "justification", "reasoning", 
                        "rationale", "notes", "considerations"
                    ]
                    
                    for field in fields_to_check:
                        if field in recommendation_json and recommendation_json[field]:
                            field_text = recommendation_json[field]
                            if isinstance(field_text, list):
                                field_text = " ".join(field_text)
                            if isinstance(field_text, str):
                                for term in score_terms:
                                    if term.lower() in field_text.lower():
                                        score_references += 1
                    
                    # Log whether scores were referenced
                    if score_references > 0:
                        logger.info(f"LLM referenced scores {score_references} times in its recommendation")
                    else:
                        logger.warning("LLM did not reference pediatric scores in its recommendation despite availability")
                        
                    # Add score utilization data to the recommendation
                    recommendation_json["score_utilization"] = {
                        "pediatric_scores_available": score_count,
                        "referenced_in_reasoning": score_references > 0,
                        "reference_count": score_references
                    }
                
                # Convert the JSON to a Recommendation object
                return self._convert_to_recommendation(recommendation_json)
                
            except Exception as e:
                logger.error(f"Error processing LLM recommendation: {str(e)}")
                # Return a properly formatted Recommendation object instead of None to avoid undefined variable errors
                return Recommendation(
                    transfer_request_id="error",
                    recommended_campus_id="ERROR",
                    confidence_score=30.0,  # Low confidence for error conditions
                    reason=f"Error processing LLM recommendation: {str(e)}",
                    notes=["Error in LLM processing", f"Error details: {str(e)}"],
                    explainability_details={"error": str(e)}
                )
                
        except Exception as e:
            error_msg = f"Error generating LLM recommendation: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            trace = traceback.format_exc()
            logger.error(f"Full traceback:\n{trace}")
            
            # Comprehensive error logging to file
            with open('/Users/derek/CascadeProjects/transfer_center/logs/recommendation_errors.log', 'a') as err_log:
                err_log.write(f"\n\n=== RECOMMENDATION ERROR {datetime.now()} ===\n")
                err_log.write(f"ERROR: {error_msg}\n")
                err_log.write(f"ERROR TYPE: {type(e).__name__}\n")
                err_log.write(f"TRACEBACK:\n{trace}\n")
                if 'prompt' in locals():
                    err_log.write(f"PROMPT SENT:\n{prompt[:1000]}...\n")
                if 'content' in locals():
                    err_log.write(f"RAW RESPONSE:\n{content}\n")
                err_log.write("=== END OF ERROR REPORT ===\n")
            
            # Log to LLM logger
            try:
                get_llm_logger().log_interaction(
                    component="RecommendationGenerator",
                    method="generate_recommendation_error",
                    input_data={
                        "extracted_entities_keys": list(extracted_entities.keys()) if extracted_entities else [],
                        "specialty_assessment_keys": list(specialty_assessment.keys()) if specialty_assessment else [],
                        "exclusion_evaluation_present": exclusion_evaluation is not None
                    },
                    output_data=None,
                    model=self.model,
                    success=False,
                    error=error_msg
                )
            except Exception as log_error:
                logger.error(f"Failed to log error to LLM logger: {log_error}")
                
            # Return a properly formatted Recommendation object instead of None to avoid undefined variable errors
            return Recommendation(
                transfer_request_id="error",
                recommended_campus_id="ERROR",
                confidence_score=20.0,  # Very low confidence for error conditions
                reason=f"Failed to generate LLM recommendation: {str(e)}",
                notes=["LLM recommendation generation failed", f"Error type: {type(e).__name__}"],
                explainability_details={"error": str(e), "traceback": trace}
            )

    def _standardize_llm_response(self, recommendation_json: Dict[str, Any]) -> Dict[str, Any]:
        """Standardize the LLM response format to ensure consistency.
        
        Args:
            recommendation_json: Raw LLM response parsed as JSON
            
        Returns:
            Standardized recommendation dictionary
        """
        logger.info("========== STANDARDIZING LLM RESPONSE ===========")
        logger.info(f"Input JSON type: {type(recommendation_json)}")
        if not isinstance(recommendation_json, dict):
            logger.error(f"Unexpected non-dict input: {recommendation_json}")
            # Return a default structure if we got something weird
            return {
                "campus_id": "Error",
                "reason": "Invalid recommendation format received",
                "confidence_score": 0.0,
                "care_level": "Unknown"
            }
        
        logger.info(f"Input JSON keys: {list(recommendation_json.keys())}")
        if len(recommendation_json.keys()) < 2:
            logger.warning(f"Sparse recommendation JSON with only {len(recommendation_json.keys())} keys")
        
        # Initialize with default values
        standardized = {
            "recommended_campus_id": recommendation_json.get("recommended_campus_id", "UnknownCampusID"),
            "recommended_campus_name": recommendation_json.get("recommended_campus_name", "Unknown Campus Name"),
            "care_level": recommendation_json.get("care_level", "General"),
            "confidence_score": recommendation_json.get("confidence_score", 70.0),
            "notes": recommendation_json.get("notes", []) if isinstance(recommendation_json.get("notes"), list) else [],
            "explainability_details": {}, # Default, will be populated below
            "transport_details": {},      # Default, will be populated below
            "conditions": {}              # Default, will be populated below
        }
        logger.debug(f"Initialized standardized structure with direct mappings and defaults for collections: {list(standardized.keys())}")
        
        # Explainability Details
        raw_explainability = recommendation_json.get("explainability_details")
        logger.debug(f"Raw explainability_details from LLM: {raw_explainability}")
        if isinstance(raw_explainability, dict):
            standardized["explainability_details"] = {
                "main_recommendation_reason": raw_explainability.get("main_recommendation_reason", "Primary reason not specified by LLM."),
                "alternative_reasons": raw_explainability.get("alternative_reasons") if isinstance(raw_explainability.get("alternative_reasons"), dict) else {},
                "key_factors_considered": raw_explainability.get("key_factors_considered") if isinstance(raw_explainability.get("key_factors_considered"), list) else [],
                "confidence_explanation": raw_explainability.get("confidence_explanation") # Optional, so None is fine
            }
        else:
            standardized["explainability_details"] = {
                "main_recommendation_reason": "Explainability details missing or malformed from LLM.",
                "alternative_reasons": {},
                "key_factors_considered": [],
                "confidence_explanation": None
            }
        standardized["reason"] = standardized["explainability_details"]["main_recommendation_reason"] # For backward compatibility / simple display
        logger.debug(f"Standardized explainability_details: {standardized['explainability_details']}")

        # Transport Details
        raw_transport_details = recommendation_json.get("transport_details")
        logger.debug(f"Raw transport_details from LLM: {raw_transport_details}")
        if isinstance(raw_transport_details, dict):
            standardized["transport_details"] = raw_transport_details
        else:
            standardized["transport_details"] = {}
            if raw_transport_details is not None:
                logger.warning(f"LLM provided transport_details of type {type(raw_transport_details)}, expected dict. Defaulting to empty dict.")
        logger.debug(f"Standardized transport_details: {standardized['transport_details']}")

        # Conditions
        raw_conditions = recommendation_json.get("conditions")
        logger.debug(f"Raw conditions from LLM: {raw_conditions}")
        if isinstance(raw_conditions, dict): # Model expects Dict[str, Any]
            standardized["conditions"] = raw_conditions
        else:
            standardized["conditions"] = {}
            if raw_conditions is not None:
                logger.warning(f"LLM provided conditions of type {type(raw_conditions)}, expected dict. Defaulting to empty dict.")
        logger.debug(f"Standardized conditions: {standardized['conditions']}")

        # Legacy field mapping for campus_id and reason if new fields were not provided
        # This is for backward compatibility if the LLM hasn't fully switched to the new schema.
        if standardized["recommended_campus_id"] == "UnknownCampusID":
            legacy_campus_id = recommendation_json.get("recommended_campus") or \
                               recommendation_json.get("campus_id") or \
                               recommendation_json.get("campus") or \
                               recommendation_json.get("hospital") or \
                               recommendation_json.get("facility")
            if legacy_campus_id:
                standardized["recommended_campus_id"] = legacy_campus_id
                standardized["recommended_campus_name"] = legacy_campus_id # Assume name is same if only legacy ID
                logger.info(f"Mapped legacy campus field to recommended_campus_id/name: {legacy_campus_id}")
        
        if standardized["reason"] == standardized["explainability_details"]["main_recommendation_reason"] and \
           standardized["reason"] in ["Primary reason not specified by LLM.", "Explainability details missing or malformed from LLM."]:
            legacy_reason_fields = ["clinical_reasoning", "reasoning", "reason", "justification", "rationale"]
            for field in legacy_reason_fields:
                if field in recommendation_json and recommendation_json[field]:
                    standardized["reason"] = recommendation_json[field]
                    standardized["explainability_details"]["main_recommendation_reason"] = recommendation_json[field]
                    logger.info(f"Used legacy reason field '{field}' for main_recommendation_reason.")
                    break
        
        # Store the original full JSON response for reference if needed, can be part of metadata or a specific field if desired
        # standardized["original_llm_response"] = recommendation_json 
                
        logger.info(f"Standardization complete. Final standardized keys: {list(standardized.keys())}")
        logger.debug(f"COMPLETE STANDARDIZED DATA (for Pydantic model):\n{json.dumps(standardized, indent=2, default=str)}")
        
        print(f"===== STANDARDIZED RECOMMENDATION (PRE-MODEL) =====\nType: {type(standardized)}\nKeys: {list(standardized.keys())}")
        print(f"Campus Name: {standardized.get('recommended_campus_name')}\nMain Reason: {standardized.get('reason')[:50]}...\nCare Level: {standardized.get('care_level')}")
        
        return standardized
    
    def _convert_to_recommendation(
        self, raw_llm_json: Dict[str, Any] # Renamed for clarity, this is the direct output from robust_json_parser
    ) -> Recommendation:
        """
        Convert the LLM recommendation JSON response to a Recommendation object.

        Args:
            recommendation_json: The parsed JSON response from the LLM

        Returns:
            Recommendation object with the appropriate fields populated
        """
        try:
            logger.info("========== CONVERTING LLM JSON TO RECOMMENDATION OBJECT (NEW) ===========")
            logger.debug(f"RAW LLM JSON for conversion:\n{json.dumps(raw_llm_json, indent=2, default=str)}")

            # Standardize the raw LLM JSON to a consistent dictionary structure
            # This handles variations and prepares for Pydantic model instantiation.
            standardized_data = self._standardize_llm_response(raw_llm_json)
            
            logger.debug(f"Data for Recommendation model instantiation (pre-Pydantic):")
            logger.debug(f"  recommended_campus_id: {standardized_data.get('recommended_campus_id')}")
            logger.debug(f"  recommended_campus_name: {standardized_data.get('recommended_campus_name')}")
            logger.debug(f"  reason (main): {standardized_data.get('reason')}") # This is main_recommendation_reason
            logger.debug(f"  confidence_score: {standardized_data.get('confidence_score')}")
            logger.debug(f"  recommended_level_of_care: {standardized_data.get('care_level')}")
            logger.debug(f"  explainability_details (dict): {standardized_data.get('explainability_details')}")
            logger.debug(f"  notes: {standardized_data.get('notes')}")
            logger.debug(f"  transport_details (dict): {standardized_data.get('transport_details')}") # Log before passing
            logger.debug(f"  conditions (dict): {standardized_data.get('conditions')}") # Log before passing


            # Now, create the Recommendation object using the standardized_data
            # The validator in Recommendation model for explainability_details will handle
            # converting the dict to an LLMReasoningDetails instance.
            
            # Ensure confidence score is a float
            confidence_score = standardized_data.get("confidence_score", 70.0)
            try:
                confidence_score = float(confidence_score)
                if not (0 <= confidence_score <= 100):
                    logger.warning(f"Confidence score {confidence_score} out of range. Clamping to 0-100.")
                    confidence_score = max(0.0, min(100.0, confidence_score))
            except (ValueError, TypeError):
                logger.error(f"Invalid confidence score format: {confidence_score}. Defaulting to 70.0.")
                confidence_score = 70.0

            recommendation_obj = Recommendation(
                transfer_request_id="llm_generated_trid", # Placeholder, will be updated by caller
                recommended_campus_id=standardized_data.get("recommended_campus_id", "UnknownCampusID"),
                recommended_campus_name=standardized_data.get("recommended_campus_name", "Unknown Campus Name"),
                reason=standardized_data.get("reason", "No primary reason provided."), # This is main_recommendation_reason
                confidence_score=confidence_score,
                recommended_level_of_care=standardized_data.get("care_level", "General"),
                explainability_details=standardized_data.get("explainability_details", {}), # This will be parsed by Pydantic validator
                notes=standardized_data.get("notes", []),
                transport_details=standardized_data.get("transport_details", {}),
                conditions=standardized_data.get("conditions", {})
            )
            
            logger.info(f"Successfully created Recommendation object. Campus: {recommendation_obj.recommended_campus_name}")
            logger.debug(f"Final Recommendation object dump:\n{recommendation_obj.model_dump_json(indent=2)}")
            
            return recommendation_obj

        except Exception as e:
            logger.error(f"Error converting standardized JSON to Recommendation object: {str(e)}", exc_info=True)
            return Recommendation(
                transfer_request_id="error_conversion",
                recommended_campus_id="ERROR_CONVERSION",
                recommended_campus_name="Error During Model Conversion",
                confidence_score=10.0,
                reason=f"Error converting LLM data to Recommendation model: {str(e)}",
                explainability_details=LLMReasoningDetails(
                    main_recommendation_reason=f"Data conversion error: {str(e)}"
                )
            )

    def _build_recommendation_prompt(
        self,
        extracted_entities: Dict[str, Any],
        specialty_assessment: Dict[str, Any],
        exclusion_evaluation: Optional[Dict[str, Any]] = None,
        available_hospitals: Optional[List[Dict[str, Any]]] = None,
        census_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, bool, int]:
        """
        Build the prompt for recommendation generation with optimized token usage.

        Args:
            extracted_entities: Dictionary of extracted clinical entities
            specialty_assessment: Dictionary with specialty need assessment
            exclusion_evaluation: Optional dictionary with exclusion criteria evaluation

        Returns:
            Tuple of (prompt text, has_scoring_data, number_of_scores)
        """
        # Extract only essential information to reduce token usage
        patient_info = self._extract_essential_patient_info(extracted_entities)
        specialty_info = self._extract_essential_specialty_info(specialty_assessment)
        exclusion_info = self._extract_essential_exclusion_info(exclusion_evaluation)

        # Check if we have scoring data
        has_scores = False
        score_count = 0
        scoring_info = ""
        
        if "scoring_results" in specialty_assessment:
            scoring_results = specialty_assessment["scoring_results"]
            if scoring_results and isinstance(scoring_results, dict):
                has_scores = True
                score_count = len(scoring_results.get("scores", {}))
                scoring_info = self._format_scoring_data(scoring_results)
        
        # Format available hospitals if provided
        hospitals_info = ""
        sending_facility_loc_data = extracted_entities.get('sending_facility_location')
        sending_facility_location_obj = None
        if sending_facility_loc_data and isinstance(sending_facility_loc_data, dict):
            s_lat = sending_facility_loc_data.get('latitude')
            s_lon = sending_facility_loc_data.get('longitude')
            if s_lat is not None and s_lon is not None:
                try:
                    sending_facility_location_obj = Location(latitude=float(s_lat), longitude=float(s_lon))
                    logger.info(f"Created Location object for sending facility: {sending_facility_location_obj}")
                except ValueError:
                    logger.error(f"Could not convert sending facility lat/lon to float: {s_lat}, {s_lon}")
            else:
                logger.warning("Sending facility location data missing latitude or longitude.")
        else:
            logger.warning("Sending facility location not found or not in expected format in extracted_entities.")

        if available_hospitals:
            logger.info(f"Using {len(available_hospitals)} hospitals for recommendation")
            # Log hospital names for debugging
            hospital_names = [h.name if h and hasattr(h, 'name') else 'Unknown Hospital' for h in available_hospitals]
            logger.info(f"Available hospitals: {hospital_names}")
            
            hospitals_info = "Available hospitals/campuses:\n"
            for i, hospital in enumerate(available_hospitals):
                name = hospital.get('name', 'Unknown Hospital')
                campus_id = hospital.get('campus_id', 'unknown')
                care_levels = hospital.get('care_levels', [])
                specialties = hospital.get('specialties', [])
                
                # Format care levels as comma-separated list or 'Unknown'
                care_levels_str = ", ".join(care_levels) if care_levels else "Unknown"
                
                # Format specialties as comma-separated list or 'None specified'
                specialties_str = ", ".join(specialties) if specialties else "None specified"
                
                # Format location info if available
                location_info = ""
                hospital_location_obj = None
                if 'location' in hospital and hospital['location']:
                    lat = hospital['location'].get('latitude')
                    lng = hospital['location'].get('longitude')
                    if lat is not None and lng is not None:
                        try:
                            hospital_location_obj = Location(latitude=float(lat), longitude=float(lng))
                            location_info = f"Location coordinates: {lat}, {lng}"
                            # Calculate and add distance if sending facility location is available
                            if sending_facility_location_obj and hospital_location_obj:
                                distance_km = calculate_distance(sending_facility_location_obj, hospital_location_obj)
                                location_info += f" (Distance: {distance_km:.1f} km)"
                            location_info += "\n"
                        except ValueError:
                            logger.error(f"Could not convert hospital lat/lon to float for {hospital.get('name', 'Unknown Hospital')}: {lat}, {lng}")
                            location_info = f"Location coordinates: {lat}, {lng} (Error converting to float)\n"
                    else:
                        location_info = "Location coordinates: Not fully available\n"
                else:
                    location_info = "Location: Not available\n"
                
                hospitals_info += f"{i+1}. {name} (ID: {campus_id})\n"
                hospitals_info += f"   Care Levels: {care_levels_str}\n"
                hospitals_info += f"   Specialties: {specialties_str}\n"
                hospitals_info += f"   {location_info}"
                
                # Add separator between hospitals
                if i < len(available_hospitals) - 1:
                    hospitals_info += "\n"
        
        # Format census data if available
        census_info = ""
        if census_data and isinstance(census_data, dict):
            census_info = "Current Hospital Census:\n"
            for campus_id, data in census_data.items():
                if isinstance(data, dict):
                    census_info += f"- {campus_id}: "
                    for unit, beds in data.items():
                        available = beds.get('available', 'Unknown')
                        total = beds.get('total', 'Unknown')
                        census_info += f"{unit}: {available}/{total} beds available, "
                    census_info = census_info.rstrip(", ") + "\n"
        
        # Build final prompt
        prompt = f"""
# Transfer Recommendation Request

## Patient Information
{patient_info}

## Specialty Assessment
{specialty_info}

## Exclusion Criteria
{exclusion_info}"""

        # Add available hospitals section if we have hospital data
        if hospitals_info:
            prompt += f"""

## Available Hospitals
{hospitals_info}"""
            
        # Add census data if available
        if census_info:
            prompt += f"""

## Bed Census
{census_info}"""

        # Add scoring data if available
        if has_scores:
            prompt += f"""
## Pediatric Scoring Data
{scoring_info}
"""

        prompt += """
## Recommendation Task
Based on the above information, provide a hospital transfer recommendation. Consider:
1. The patient's care needs and suggested care level
2. Any excluded campuses or specialties
3. Proximity to the patient's location
4. Availability of required services
5. Current bed availability
"""

        # Add explanation of how to use scoring data if available
        if has_scores:
            prompt += """
6. Pediatric severity scores should heavily influence your recommendation, especially:
   - Use PEWS, TRAP scores to determine transport requirements
   - Use PRISM III scores to assess mortality risk
   - Use CAMEO II scores to determine nursing care needs
   - Explicitly reference the scores in your reasoning
"""

        # Log the prompt size
        logger.debug(f"Recommendation prompt size: {len(prompt)} characters")
        
        return prompt, has_scores, score_count

    def _extract_essential_patient_info(self, entities: Dict[str, Any]) -> str:
        """Extract the most relevant patient information in a concise format."""
        if not entities:
            return "No patient information available."

        # Extract demographics
        demographics = entities.get("demographics", {})
        age = demographics.get("age", "Unknown age")
        gender = demographics.get("gender", "Unknown gender")
        weight = demographics.get("weight", "Unknown weight")

        # Extract vital signs
        vital_signs = entities.get("vital_signs", {})
        vitals_text = []
        for vital_key, display_name in [
            ("hr", "Heart Rate"),
            ("rr", "Respiratory Rate"),
            ("bp", "Blood Pressure"),
            ("temp", "Temperature"),
            ("o2", "O2 Saturation"),
        ]:
            if vital_key in vital_signs:
                vitals_text.append(f"- {display_name}: {vital_signs[vital_key]}")

        # Extract clinical information
        clinical_info = entities.get("clinical_information", entities.get("clinical_info", {}))
        chief_complaint = clinical_info.get("chief_complaint", "Unknown")
        clinical_history = clinical_info.get("clinical_history", "No history provided")

        # Format the output
        output = f"- Demographics: {age}, {gender}, {weight}\n"
        
        if vitals_text:
            output += "- Vital Signs:\n  " + "\n  ".join(vitals_text) + "\n"
            
        output += f"- Chief Complaint: {chief_complaint}\n"
        output += f"- Clinical History: {clinical_history}\n"
        
        # Add any diagnoses if available
        if "diagnoses" in clinical_info and clinical_info["diagnoses"]:
            diagnoses = clinical_info["diagnoses"]
            if isinstance(diagnoses, list):
                diagnoses_text = ", ".join(diagnoses)
            else:
                diagnoses_text = str(diagnoses)
            output += f"- Diagnoses: {diagnoses_text}\n"
            
        return output

    def _extract_essential_specialty_info(self, assessment: Dict[str, Any]) -> str:
        """Extract the most relevant specialty assessment information."""
        if not assessment:
            return "No specialty assessment available."

        output = []

        # Get care level recommendation
        if "recommended_care_level" in assessment:
            output.append(f"- Recommended Care Level: {assessment['recommended_care_level']}")
            
            # Add care level reasoning if available
            if "care_level_reasoning" in assessment:
                output.append(f"- Care Level Reasoning: {assessment['care_level_reasoning']}")

        # Get required specialties
        if "required_specialties" in assessment:
            specialties = assessment["required_specialties"]
            if specialties:
                if isinstance(specialties, list):
                    # Handle both string list and dict list formats
                    specialty_names = []
                    for spec in specialties:
                        if isinstance(spec, dict) and "specialty" in spec:
                            specialty_names.append(f"{spec['specialty']} (Confidence: {spec.get('confidence', 'Unknown')}%)")
                        elif isinstance(spec, str):
                            specialty_names.append(spec)
                    output.append(f"- Required Specialties: {', '.join(specialty_names)}")
                else:
                    output.append(f"- Required Specialties: {specialties}")

        # Return the formatted output
        return "\n".join(output) if output else "No specific specialty needs identified."

    def _extract_essential_exclusion_info(
        self, exclusion: Optional[Dict[str, Any]]
    ) -> str:
        """Extract essential exclusion information."""
        if not exclusion:
            return "No exclusion criteria evaluated."

        output = []

        # Get excluded campuses
        if "excluded_campuses" in exclusion and exclusion["excluded_campuses"]:
            excluded = exclusion["excluded_campuses"]
            if isinstance(excluded, list):
                output.append(f"- Excluded Campuses: {', '.join(excluded)}")
            else:
                output.append(f"- Excluded Campuses: {excluded}")

        # Get exclusion reasons
        if "exclusion_reasons" in exclusion and exclusion["exclusion_reasons"]:
            reasons = exclusion["exclusion_reasons"]
            if isinstance(reasons, dict):
                reason_texts = []
                for campus, reason in reasons.items():
                    reason_texts.append(f"{campus}: {reason}")
                output.append("- Exclusion Reasons:\n  - " + "\n  - ".join(reason_texts))
            else:
                output.append(f"- Exclusion Reasons: {reasons}")

        # Get recommended campus if available
        if "recommended_campus" in exclusion and exclusion["recommended_campus"]:
            output.append(f"- Recommended Campus from Exclusion Analysis: {exclusion['recommended_campus']}")

        # Return the formatted output
        return "\n".join(output) if output else "No specific exclusion criteria identified."

    def _format_scoring_data(self, scoring_results: Dict[str, Any]) -> str:
        """
        Format the pediatric scoring data in a comprehensive way for the LLM.
        
        This method prepares the scoring data with complete details including subscores,
        interpretations, and care recommendations to help the LLM make an informed decision.
        
        Args:
            scoring_results: Dictionary containing score results and care level recommendations
            
        Returns:
            Formatted string with comprehensive scoring information
        """
        if not scoring_results or not isinstance(scoring_results, dict):
            return "No pediatric scoring data available."
            
        formatted_text = ""
        
        # Process each score type
        if "scores" in scoring_results and scoring_results["scores"]:
            scores = scoring_results["scores"]
            
            # PEWS (Pediatric Early Warning Score)
            if "pews" in scores:
                pews = scores["pews"]
                formatted_text += "### PEWS (Pediatric Early Warning Score)\n"
                formatted_text += f"- Total Score: {pews.get('total_score', 'N/A')}\n"
                formatted_text += f"- Interpretation: {pews.get('interpretation', 'N/A')}\n"
                
                # Add subscores if available
                if "subscores" in pews:
                    subscores = pews["subscores"]
                    formatted_text += "- Subscores:\n"
                    for subscore_name, value in subscores.items():
                        formatted_text += f"  - {subscore_name}: {value}\n"
                
                # Add recommended actions
                if "recommended_actions" in pews:
                    actions = pews["recommended_actions"]
                    formatted_text += "- Recommended Actions:\n"
                    if isinstance(actions, list):
                        for action in actions:
                            formatted_text += f"  - {action}\n"
                    else:
                        formatted_text += f"  - {actions}\n"
                
                formatted_text += "\n"
            
            # TRAP (Transport Risk Assessment in Pediatrics)
            if "trap" in scores:
                trap = scores["trap"]
                formatted_text += "### TRAP (Transport Risk Assessment in Pediatrics)\n"
                formatted_text += f"- Total Score: {trap.get('total_score', 'N/A')}\n"
                formatted_text += f"- Risk Level: {trap.get('risk_level', 'N/A')}\n"
                
                # Add subscores
                if "subscores" in trap:
                    subscores = trap["subscores"]
                    formatted_text += "- System Assessments:\n"
                    for system, value in subscores.items():
                        formatted_text += f"  - {system}: {value}\n"
                
                # Add transport team recommendation
                if "transport_team_recommendation" in trap:
                    formatted_text += f"- Transport Team: {trap['transport_team_recommendation']}\n"
                
                formatted_text += "\n"
            
            # PRISM III
            if "prism_iii" in scores:
                prism = scores["prism_iii"]
                formatted_text += "### PRISM III (Pediatric Risk of Mortality)\n"
                formatted_text += f"- Total Score: {prism.get('total_score', 'N/A')}\n"
                formatted_text += f"- Mortality Risk: {prism.get('mortality_risk', 'N/A')}\n"
                
                # Add variable scores
                if "variable_scores" in prism:
                    variables = prism["variable_scores"]
                    formatted_text += "- Physiologic Variables:\n"
                    for variable, value in variables.items():
                        formatted_text += f"  - {variable}: {value}\n"
                
                formatted_text += "\n"
            
            # CAMEO II
            if "cameo_ii" in scores:
                cameo = scores["cameo_ii"]
                formatted_text += "### CAMEO II (Complexity Assessment and Monitoring)\n"
                formatted_text += f"- Total Score: {cameo.get('total_score', 'N/A')}\n"
                formatted_text += f"- Acuity Level: {cameo.get('acuity_level', 'N/A')}\n"
                
                # Add domain scores
                if "domain_scores" in cameo:
                    domains = cameo["domain_scores"]
                    formatted_text += "- Domain Scores:\n"
                    for domain, value in domains.items():
                        formatted_text += f"  - {domain}: {value}\n"
                
                # Add staffing recommendation
                if "recommended_nurse_ratio" in cameo:
                    formatted_text += f"- Recommended Nurse Ratio: {cameo['recommended_nurse_ratio']}\n"
                
                formatted_text += "\n"
                
        # Add recommended care level information
        if "recommended_care_levels" in scoring_results:
            care_levels = scoring_results["recommended_care_levels"]
            formatted_text += "### Care Level Recommendations Based on Scores\n"
            
            # Handle both list and dictionary formats
            if isinstance(care_levels, dict):
                # Dictionary format with score_name: level pairs
                for score_name, level in care_levels.items():
                    formatted_text += f"- {score_name}: {level}\n"
            elif isinstance(care_levels, list):
                # List format with just the levels
                for level in care_levels:
                    formatted_text += f"- Recommended: {level}\n"
            else:
                # Single string format
                formatted_text += f"- Recommended: {care_levels}\n"
            
            formatted_text += "\n"
            
        # Add justifications for score-based recommendations
        if "justifications" in scoring_results:
            justifications = scoring_results["justifications"]
            formatted_text += "### Score-Based Justifications\n"
            
            # Handle both list and dictionary formats for justifications
            if isinstance(justifications, dict):
                # Dictionary format with score_name: justification pairs
                for score_name, justification in justifications.items():
                    formatted_text += f"- {score_name}: {justification}\n"
            elif isinstance(justifications, list):
                # List format with just the justifications
                for i, justification in enumerate(justifications):
                    formatted_text += f"- Justification {i+1}: {justification}\n"
            else:
                # Single string format
                formatted_text += f"- Justification: {justifications}\n"
                
        return formatted_text
