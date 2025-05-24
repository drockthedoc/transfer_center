"""
Robust recommendation handling for the Transfer Center application.

This module implements robust handling of LLM recommendations with comprehensive
error handling, fallbacks, and recovery mechanisms.
"""

import logging
import json
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from src.core.models import Recommendation

logger = logging.getLogger(__name__)

class RecommendationHandler:
    """Handles robust recommendation processing with comprehensive error handling.
    
    This class provides methods for:
    1. Extracting recommendations from LLM responses with multiple fallback approaches
    2. Creating standardized error recommendations
    3. Rule-based extraction as a fallback mechanism when LLM processing fails
    4. Special handling for extracting JSON from Markdown code blocks
    
    The fallback hierarchy is:
    1. Try LLM extraction with multiple parsing approaches
    2. If LLM fails, fall back to rule-based extraction
    3. If all else fails, create an error recommendation
    """
    
    # Campus information - would typically be loaded from a configuration file
    CAMPUS_INFO = {
        "CAMPUS_A": {"name": "Main Campus", "services": ["general", "picu", "nicu", "trauma"]},
        "CAMPUS_B": {"name": "North Campus", "services": ["general", "picu"]},
        "CAMPUS_C": {"name": "South Campus", "services": ["general", "burns"]},
        "CAMPUS_D": {"name": "East Campus", "services": ["general", "neuro"]},
    }
    
    @staticmethod
    def create_error_recommendation(request_id: str, error_message: str, confidence: float = 10.0) -> Recommendation:
        """Create a standardized error recommendation.
        
        Args:
            request_id: The ID of the transfer request
            error_message: The error message to include in the recommendation
            confidence: Confidence score for the error recommendation (default: 10.0)
            
        Returns:
            A Recommendation object with error details
        """
        return Recommendation(
            transfer_request_id=request_id,
            recommended_campus_id="ERROR",
            reason=f"Error: {error_message}",
            confidence_score=confidence,
            notes=[
                "Error occurred during recommendation generation",
                f"Error details: {error_message}"
            ],
            explainability_details={"error": error_message}
        )
    
    @staticmethod
    def extract_json_from_markdown(text: str) -> Dict[str, Any]:
        """Extract JSON data from Markdown code blocks.
        
        This method handles the common case where LLMs return JSON wrapped in
        Markdown code blocks like ```json { ... } ```
        
        Args:
            text: Text potentially containing JSON in Markdown code blocks
            
        Returns:
            Extracted JSON data as a dictionary or empty dict if no valid JSON found
        """
        import re
        import json
        
        logger.info("Attempting to extract JSON from potential Markdown code blocks")
        
        # Try to find JSON in Markdown code blocks (```json ... ``` format)
        code_block_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        code_blocks = re.findall(code_block_pattern, text)
        
        # If we found code blocks, try to parse each one as JSON
        for block in code_blocks:
            try:
                # Clean up the block (remove any extra backticks or spaces)
                clean_block = block.strip()
                parsed_data = json.loads(clean_block)
                logger.info(f"Successfully extracted JSON from Markdown code block")
                return parsed_data
            except json.JSONDecodeError:
                logger.warning(f"Found code block but it's not valid JSON")
                continue
        
        # If no code blocks with valid JSON were found, try to extract JSON directly
        # Look for content that looks like JSON (starts with { and ends with })
        json_pattern = r"\{[\s\S]*\}"
        json_matches = re.findall(json_pattern, text)
        
        for potential_json in json_matches:
            try:
                parsed_data = json.loads(potential_json)
                logger.info(f"Successfully extracted JSON directly from text")
                return parsed_data
            except json.JSONDecodeError:
                logger.warning(f"Found JSON-like text but it's not valid JSON")
                continue
        
        # If all attempts failed, return empty dict
        logger.warning("Could not extract any valid JSON from the text")
        return {}
    
    @staticmethod
    def extract_recommendation(extracted_data: Dict[str, Any], request_id: str) -> Recommendation:
        """Extract recommendation from LLM response data with robust error handling.
        
        This method tries multiple approaches to extract a valid recommendation:
        1. From recommendation_data field (preferred format)
        2. From final_recommendation object 
        3. From recommended_campus dictionary
        4. Falls back to error recommendation if all approaches fail
        
        Args:
            extracted_data: Dictionary containing LLM extracted data
            request_id: The ID of the transfer request
            
        Returns:
            A valid Recommendation object, even in error cases
        """
        # Log all available data keys for diagnosis
        data_keys = list(extracted_data.keys())
        logger.info(f"Available data keys: {data_keys}")
        print(f"ALL AVAILABLE KEYS: {data_keys}")
        
        # APPROACH 1: Check for recommendation_data (preferred format)
        final_recommendation = None
        
        if "recommendation_data" in extracted_data:
            try:
                data = extracted_data["recommendation_data"]
                print(f"Found recommendation_data: {type(data)}")
                
                if isinstance(data, dict):
                    print(f"Recommendation data keys: {list(data.keys())}")
                    final_recommendation = Recommendation(
                        transfer_request_id=data.get("transfer_request_id", request_id),
                        recommended_campus_id=data.get("recommended_campus_id", "UNKNOWN"),
                        reason=data.get("reason", "No reason provided"),
                        confidence_score=data.get("confidence_score", 50.0),
                        notes=data.get("notes", [])
                    )
                    logger.info("Successfully created Recommendation from recommendation_data")
            except Exception as parse_error:
                logger.error(f"Error parsing recommendation_data: {parse_error}")
                # Continue to next approach, don't return yet
        
        # APPROACH 2: Check for final_recommendation object
        if not final_recommendation and "final_recommendation" in extracted_data:
            try:
                rec_obj = extracted_data["final_recommendation"]
                print(f"Found final_recommendation object: {type(rec_obj)}")
                
                if isinstance(rec_obj, Recommendation):
                    final_recommendation = rec_obj
                    logger.info("Using direct Recommendation object")
                elif isinstance(rec_obj, dict):
                    # Convert dictionary to Recommendation
                    campus_id = rec_obj.get("recommended_campus_id", rec_obj.get("recommended_campus", "UNKNOWN"))
                    reason = rec_obj.get("reason", rec_obj.get("clinical_reasoning", "No reason provided"))
                    
                    final_recommendation = Recommendation(
                        transfer_request_id=request_id,
                        recommended_campus_id=campus_id,
                        reason=reason,
                        confidence_score=rec_obj.get("confidence_score", 50.0),
                        notes=rec_obj.get("notes", []),
                        explainability_details=rec_obj
                    )
                    logger.info("Converted dictionary to Recommendation object")
            except Exception as obj_error:
                logger.error(f"Error processing final_recommendation: {obj_error}")
                # Continue to next approach
        
        # APPROACH 3: Check for recommended_campus dictionary
        if not final_recommendation and "recommended_campus" in extracted_data:
            try:
                rec_dict = extracted_data["recommended_campus"]
                print(f"Found recommended_campus data: {type(rec_dict)}")
                
                if isinstance(rec_dict, dict):
                    campus_id = rec_dict.get("campus_id", rec_dict.get("recommended_campus", "UNKNOWN"))
                    reason = rec_dict.get("reason", rec_dict.get("clinical_reasoning", "No reason provided"))
                    
                    final_recommendation = Recommendation(
                        transfer_request_id=request_id,
                        recommended_campus_id=campus_id,
                        reason=reason,
                        confidence_score=rec_dict.get("confidence_score", 50.0),
                        explainability_details=rec_dict
                    )
                    logger.info("Created Recommendation from recommended_campus dictionary")
            except Exception as dict_error:
                logger.error(f"Error processing recommended_campus: {dict_error}")
                # Last approach failed, will use fallback
        
        # FALLBACK: If all extraction approaches failed, create a generic error recommendation
        if not final_recommendation:
            logger.warning("All recommendation extraction approaches failed")
            final_recommendation = RecommendationHandler.create_error_recommendation(
                request_id=request_id,
                error_message="Could not extract a valid recommendation from LLM response",
                confidence=5.0  # Very low confidence
            )
        
        # Ensure recommendation has the correct request ID
        final_recommendation.transfer_request_id = request_id
        
        # Mark this as an LLM-generated recommendation for display purposes
        # Update or create the explainability details dictionary
        if not hasattr(final_recommendation, 'explainability_details') or final_recommendation.explainability_details is None:
            final_recommendation.explainability_details = {}
        
        # Add extraction method if it's not an error recommendation
        if final_recommendation.recommended_campus_id != "ERROR":
            final_recommendation.explainability_details["extraction_method"] = "llm"
            final_recommendation.explainability_details["note"] = "Generated using LLM processing"
            
            # Add a note to indicate LLM processing was used
            if not hasattr(final_recommendation, 'notes') or final_recommendation.notes is None:
                final_recommendation.notes = []
            final_recommendation.notes.append("Generated using AI/LLM processing")
        
        # Add detailed debug output
        print(f"===== FINAL RECOMMENDATION =====")
        print(f"Type: {type(final_recommendation)}")
        print(f"Campus: {final_recommendation.recommended_campus_id}")
        print(f"Confidence: {final_recommendation.confidence_score}")
        print(f"Reason: {final_recommendation.reason[:100]}...")
        
        return final_recommendation
    
    @staticmethod
    def extract_rule_based_recommendation(clinical_text: str, request_id: str, scoring_results: Optional[Dict[str, Any]] = None) -> Recommendation:
        """Extract a recommendation using rule-based methods when LLM fails.
        
        This is a fallback mechanism that uses pattern matching and basic rules to determine
        the appropriate campus for a transfer when the LLM approach fails.
        
        Args:
            clinical_text: The raw clinical text to analyze
            request_id: The ID of the transfer request
            scoring_results: Optional pediatric scoring results if available
            
        Returns:
            A Recommendation object based on rule-based extraction
        """
        import re
        
        logger.info("Falling back to rule-based recommendation extraction")
        
        # Extract basic data using pattern matching
        extracted_data = RecommendationHandler._extract_basic_data(clinical_text)
        
        # Determine care level based on keywords and vital signs
        care_level = "General"
        keywords = []
        
        # Extract keywords for conditions
        condition_patterns = {
            "trauma": r"(?:trauma|accident|crash|fall|injury)",
            "burns": r"(?:burn|scald|thermal injury)",
            "respiratory": r"(?:breathing difficulty|respiratory distress|intubated|ventilator)",
            "cardiac": r"(?:cardiac|heart failure|arrhythmia|chest pain)",
            "neuro": r"(?:seizure|stroke|neurological|unresponsive|altered mental status)",
            "sepsis": r"(?:sepsis|septic|infection)",
            "nicu": r"(?:newborn|infant|premature|preterm|neonatal)",
            "picu": r"(?:child|pediatric intensive care)"
        }
        
        # Search for conditions in the clinical text
        for condition, pattern in condition_patterns.items():
            if re.search(pattern, clinical_text, re.IGNORECASE):
                keywords.append(condition)
        
        # Determine critical keywords that would trigger higher levels of care
        critical_keywords = ["trauma", "respiratory", "cardiac", "neuro"]
        picu_keywords = ["picu"]
        nicu_keywords = ["nicu"]
        
        # Check vital signs for abnormalities
        vital_signs = extracted_data.get("vital_signs", {})
        vital_sign_abnormalities = []
        
        # Simplified vital sign analysis
        if vital_signs.get("heart_rate", 0) > 120:
            vital_sign_abnormalities.append("tachycardia")
        if vital_signs.get("systolic_bp", 120) < 90:
            vital_sign_abnormalities.append("hypotension")
        if vital_signs.get("oxygen_saturation", 100) < 92:
            vital_sign_abnormalities.append("hypoxia")
        
        # Determine care level based on keywords and vital signs
        if any(keyword in nicu_keywords for keyword in keywords):
            care_level = "NICU"
        elif any(keyword in picu_keywords for keyword in keywords):
            care_level = "PICU"
        elif any(keyword in critical_keywords for keyword in keywords) or vital_sign_abnormalities:
            care_level = "ICU"
        
        # Use pediatric scoring results if available to further refine care level
        if scoring_results:
            try:
                # Extract score values
                scores = scoring_results.get("scores", {})
                score_recommendations = []
                
                # Use PEWS (Pediatric Early Warning Score) if available
                if "pews" in scores:
                    pews_score = scores["pews"].get("total_score", 0)
                    pews_rec = scores["pews"].get("recommendation", "")
                    score_recommendations.append(f"PEWS: {pews_score} - {pews_rec}")
                    if pews_score >= 7:
                        care_level = "PICU"
                    elif pews_score >= 5:
                        care_level = "ICU"
                
                # Use TRAP (Transport Risk Assessment in Pediatrics) if available
                if "trap" in scores:
                    trap_risk = scores["trap"].get("risk_level", "")
                    trap_rec = scores["trap"].get("recommendation", "")
                    score_recommendations.append(f"TRAP: {trap_risk} - {trap_rec}")
                    if trap_risk == "High":
                        care_level = "PICU"
                    elif trap_risk == "Medium" and care_level == "General":
                        care_level = "ICU"
                
                # Use CAMEO II for nursing workload assessment
                if "cameo" in scores:
                    cameo_score = scores["cameo"].get("total_score", 0)
                    cameo_rec = scores["cameo"].get("recommendation", "")
                    score_recommendations.append(f"CAMEO II: {cameo_score} - {cameo_rec}")
                    if cameo_score >= 25:  # High acuity/workload
                        if care_level == "General":
                            care_level = "ICU"
                
                # Use PRISM III for mortality risk
                if "prism" in scores:
                    prism_score = scores["prism"].get("total_score", 0)
                    prism_rec = scores["prism"].get("recommendation", "")
                    score_recommendations.append(f"PRISM III: {prism_score} - {prism_rec}")
                    if prism_score >= 10:  # Higher mortality risk
                        care_level = "PICU"
                    elif prism_score >= 5 and care_level == "General":
                        care_level = "ICU"
                
                # Queensland Pediatric Scores
                if "queensland" in scores:
                    qld_score = scores["queensland"].get("total_score", 0)
                    qld_rec = scores["queensland"].get("recommendation", "")
                    score_recommendations.append(f"Queensland: {qld_score} - {qld_rec}")
                    # Use Queensland recommendations if provided
                    if "PICU" in qld_rec:
                        care_level = "PICU"
                    elif "ICU" in qld_rec and care_level == "General":
                        care_level = "ICU"
                
                # Transport Physiology Score
                if "tps" in scores:
                    tps_score = scores["tps"].get("total_score", 0)
                    tps_rec = scores["tps"].get("recommendation", "")
                    score_recommendations.append(f"TPS: {tps_score} - {tps_rec}")
                    if tps_score >= 8:
                        care_level = "PICU"
                    elif tps_score >= 5 and care_level == "General":
                        care_level = "ICU"
                
                # Children's Hospital Early Warning Score
                if "chews" in scores:
                    chews_score = scores["chews"].get("total_score", 0)
                    chews_rec = scores["chews"].get("recommendation", "")
                    score_recommendations.append(f"CHEWS: {chews_score} - {chews_rec}")
                    if chews_score >= 5:
                        care_level = "PICU"
                    elif chews_score >= 3 and care_level == "General":
                        care_level = "ICU"
                
                # We'll collect score recommendations but not modify extracted_data directly
                # Store for later use in explainability details
                
            except Exception as score_error:
                logger.error(f"Error processing scoring results: {score_error}")
        
        # Match the care level to the appropriate campus
        campus_id = "CAMPUS_A"  # Default to main campus
        confidence_score = 40.0  # Lower confidence for rule-based approach
        
        # Simple campus selection logic
        if care_level == "NICU":
            campus_id = "CAMPUS_A"  # Only main campus has NICU
            confidence_score = 70.0
        elif care_level == "PICU":
            # Both main and north campus have PICU - choose based on other factors
            if "trauma" in keywords:
                campus_id = "CAMPUS_A"  # Main campus for trauma cases
            else:
                campus_id = "CAMPUS_B"  # North campus for other PICU cases
            confidence_score = 60.0
        elif "burns" in keywords:
            campus_id = "CAMPUS_C"  # South campus for burns
            confidence_score = 65.0
        elif "neuro" in keywords:
            campus_id = "CAMPUS_D"  # East campus for neuro
            confidence_score = 65.0
        
        # Prepare detailed reasoning for recommendation
        reasoning = []
        reasoning.append(f"Care level determination: {care_level}")
        
        if keywords:
            reasoning.append(f"Identified conditions: {', '.join(keywords)}")
        
        if vital_sign_abnormalities:
            reasoning.append(f"Vital sign abnormalities: {', '.join(vital_sign_abnormalities)}")
        
        if 'score_recommendations' in locals() and score_recommendations:
            reasoning.append("Pediatric scoring results:")
            for score_rec in score_recommendations:
                reasoning.append(f"  - {score_rec}")
        
        # Create the recommendation
        recommendation = Recommendation(
            transfer_request_id=request_id,
            recommended_campus_id=campus_id,
            reason=f"Rule-based recommendation based on {care_level} care level" + 
                   (f" and identified conditions: {', '.join(keywords)}" if keywords else "."),
            confidence_score=confidence_score,
            notes=[
                f"Note: This is a RULE-BASED recommendation (LLM processing was not available)"
            ] + reasoning,
            explainability_details={
                "extraction_method": "rule_based",
                "note": "Generated using pattern matching and rule-based extraction",
                "care_level": care_level,
                "identified_conditions": keywords,
                "vital_sign_abnormalities": vital_sign_abnormalities,
                "scoring_recommendations": score_recommendations if 'score_recommendations' in locals() else [],
                "confidence_score": confidence_score
            }
        )
        
        logger.info(f"Generated rule-based recommendation: {campus_id} (confidence: {confidence_score}%)")
        return recommendation
    
    @staticmethod
    def _extract_basic_data(clinical_text: str) -> Dict[str, Any]:
        """Extract basic patient data from clinical text using regex pattern matching.
        
        Args:
            clinical_text: The raw clinical text to analyze
            
        Returns:
            Dictionary with extracted data including vital signs
        """
        import re
        
        # Initialize extracted data
        extracted_data = {}
        vital_signs = {}
        
        # Extract age using regex
        age_match = re.search(
            r"(\d+)(?:\s*-|\s+)(?:year|yr|y)[s\s]*(?:old)?",
            clinical_text,
            re.IGNORECASE,
        )
        if age_match:
            extracted_data["age"] = int(age_match.group(1))
        
        # Extract vital signs using regex
        
        # Heart rate (HR, pulse)
        hr_match = re.search(
            r"(?:hr|heart rate|pulse)[\s:=]*(\d{2,3})(?:\s*bpm)?", 
            clinical_text, 
            re.IGNORECASE
        )
        if hr_match:
            vital_signs["heart_rate"] = int(hr_match.group(1))
        
        # Blood pressure (BP)
        bp_match = re.search(
            r"(?:bp|blood pressure)[\s:=]*(\d{2,3})[/\\](\d{2,3})", 
            clinical_text, 
            re.IGNORECASE
        )
        if bp_match:
            vital_signs["systolic_bp"] = int(bp_match.group(1))
            vital_signs["diastolic_bp"] = int(bp_match.group(2))
        
        # Respiratory rate (RR)
        rr_match = re.search(
            r"(?:rr|resp|respiratory rate)[\s:=]*(\d{1,2})(?:\s*bpm)?", 
            clinical_text, 
            re.IGNORECASE
        )
        if rr_match:
            vital_signs["respiratory_rate"] = int(rr_match.group(1))
        
        # Oxygen saturation (O2 sat, SpO2)
        o2_match = re.search(
            r"(?:o2 sat|spo2|oxygen saturation|o2)[\s:=]*(\d{1,3})(?:\s*%|\s*percent)?", 
            clinical_text, 
            re.IGNORECASE
        )
        if o2_match:
            sat_value = int(o2_match.group(1))
            # Validate the value is in a reasonable range
            if 1 <= sat_value <= 100:
                vital_signs["oxygen_saturation"] = sat_value
        
        # Temperature (temp)
        temp_match = re.search(
            r"(?:temp|temperature)[\s:=]*(\d{2}(?:\.\d)?)(?:\s*(?:c|celsius|f|fahrenheit))?", 
            clinical_text, 
            re.IGNORECASE
        )
        if temp_match:
            vital_signs["temperature"] = float(temp_match.group(1))
        
        # Weight in kg
        weight_match = re.search(
            r"(?:weight)[\s:=]*(\d+\.?\d*)\s*(?:kg)", clinical_text, re.IGNORECASE
        )
        if weight_match:
            extracted_data["weight_kg"] = float(weight_match.group(1))
        
        # Add vital signs to extracted data
        extracted_data["vital_signs"] = vital_signs
        
        return extracted_data
