"""
LLM Interface Module

This module integrates the LLM prompt chaining system with the Transfer Center application.
It provides a high-level interface for the application to use LLM-powered analysis
while handling fallbacks and error scenarios.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from src.core.exclusion_checker import check_exclusions, load_exclusion_criteria
from src.core.models import HospitalCampus, PatientData
from src.llm.classification import determine_care_level, parse_patient_text
from src.llm.llm_client import get_llm_client
from src.llm.prompt_chain import analyze_clinical_vignette

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMInterface:
    """
    Interface for LLM-powered analysis in the Transfer Center application.
    Integrates prompt chaining with existing functionality and handles fallbacks.
    """

    def __init__(self):
        """Initialize the LLM interface."""
        self.llm_client = get_llm_client()
        self.exclusion_criteria = load_exclusion_criteria()

    def analyze_patient_for_transfer(
        self, patient_vignette: str, target_campuses: List[HospitalCampus]
    ) -> Dict[str, Any]:
        """
        Analyze a patient vignette for transfer to potential target campuses.

        Args:
            patient_vignette: Raw clinical vignette text
            target_campuses: List of potential target campuses

        Returns:
            Dictionary with analysis results including:
            - extracted_patient_data: Structured patient data
            - campus_analyses: Analyses for each target campus
            - recommended_campus: Recommended target campus
            - recommended_care_level: Recommended care level
            - explanation: Explanation of the recommendation
        """
        logger.info("Starting patient analysis for transfer")

        # Step 1: Extract patient data (with robust fallback)
        patient_data, extraction_source = self._extract_patient_data_with_fallback(
            patient_vignette
        )

        # Step 2: Analyze each target campus
        campus_analyses = []

        for campus in target_campuses:
            try:
                # Use the prompt chaining system for detailed analysis
                campus_analysis = self._analyze_campus_for_patient(
                    patient_vignette, patient_data, campus
                )
                campus_analyses.append(campus_analysis)
            except Exception as e:
                logger.error(f"Error analyzing campus {campus.name}: {e}")
                # Fallback to simpler analysis if the prompt chain fails
                campus_analysis = self._fallback_campus_analysis(patient_data, campus)
                campus_analyses.append(campus_analysis)

        # Step 3: Determine best campus based on analyses
        recommended_campus, care_level, explanation = (
            self._determine_recommended_campus(
                patient_data, target_campuses, campus_analyses
            )
        )

        # Compile final results
        results = {
            "extracted_patient_data": {
                "age": getattr(patient_data, "age", None),
                "weight_kg": getattr(patient_data, "weight_kg", None),
                "sex": getattr(patient_data, "sex", None),
                "chief_complaint": getattr(patient_data, "chief_complaint", None),
                "clinical_history": getattr(patient_data, "clinical_history", None),
                "vital_signs": getattr(patient_data, "vital_signs", {}),
                "extraction_source": extraction_source,
            },
            "campus_analyses": campus_analyses,
            "recommended_campus": {
                "id": recommended_campus.campus_id if recommended_campus else None,
                "name": recommended_campus.name if recommended_campus else None,
            },
            "recommended_care_level": care_level,
            "explanation": explanation,
        }

        return results

    def _extract_patient_data_with_fallback(
        self, patient_vignette: str
    ) -> Tuple[PatientData, str]:
        """
        Extract patient data from vignette with robust fallback mechanisms.

        Args:
            patient_vignette: Raw clinical vignette text

        Returns:
            Tuple of (PatientData, extraction_source)
        """
        # Try rule-based extraction first (our most reliable method)
        try:
            patient_data = parse_patient_text(patient_vignette)
            return patient_data, "rule_based"
        except Exception as e:
            logger.warning(f"Rule-based extraction failed: {e}")

            # Try LLM-based extraction as fallback
            try:
                # Use LLM client to extract structured data
                prompt = f"""
                Extract the following information from this patient vignette in JSON format:

                {patient_vignette}

                Return a JSON object with these fields:
                - age: patient age (numeric)
                - weight_kg: weight in kg (numeric)
                - sex: patient sex (string)
                - chief_complaint: main complaint (string)
                - clinical_history: medical history (string)
                - vital_signs: object with bp, hr, rr, temp, o2sat (all numeric)
                """

                llm_response = self.llm_client.generate(prompt)

                # Extract JSON from response
                try:
                    start_idx = llm_response.find("{")
                    end_idx = llm_response.rfind("}") + 1
                    if start_idx >= 0 and end_idx > start_idx:
                        json_str = llm_response[start_idx:end_idx]
                        data = json.loads(json_str)

                        # Create PatientData object
                        patient_data = PatientData(
                            age=data.get("age"),
                            weight_kg=data.get("weight_kg"),
                            sex=data.get("sex", ""),
                            chief_complaint=data.get("chief_complaint", ""),
                            clinical_history=data.get("clinical_history", ""),
                            vital_signs=data.get("vital_signs", {}),
                        )
                        return patient_data, "llm"
                except Exception as json_e:
                    logger.error(f"Failed to parse LLM JSON response: {json_e}")

            except Exception as llm_e:
                logger.error(f"LLM-based extraction failed: {llm_e}")

            # Last resort: Create minimal PatientData from the raw text
            minimal_data = PatientData(
                chief_complaint="Unknown (extraction failed)",
                clinical_history=patient_vignette[
                    :500
                ],  # Use truncated vignette as history
            )
            return minimal_data, "minimal_fallback"

    def _analyze_campus_for_patient(
        self, patient_vignette: str, patient_data: PatientData, campus: HospitalCampus
    ) -> Dict[str, Any]:
        """
        Perform detailed analysis of a campus for a patient.

        Args:
            patient_vignette: Raw clinical vignette text
            patient_data: Structured patient data
            campus: Hospital campus to analyze

        Returns:
            Dictionary with campus analysis results
        """
        # Step 1: Check exclusions using rule-based approach
        exclusions = check_exclusions(patient_data, campus)

        # Step 2: Use prompt chaining for comprehensive analysis
        llm_analysis = analyze_clinical_vignette(
            patient_vignette, campus.name, self.llm_client, self.exclusion_criteria
        )

        # Step 3: Combine rule-based and LLM results
        combined_exclusions = []

        # Add rule-based exclusions
        for excl in exclusions:
            combined_exclusions.append(
                {
                    "name": excl.name,
                    "description": excl.description,
                    "source": "rule_based",
                }
            )

        # Add LLM-identified exclusions
        for excl in llm_analysis.get("exclusion_criteria_evaluation", []):
            if excl.get("status") == "likely_met":
                combined_exclusions.append(
                    {
                        "name": f"LLM-Identified: {
                            excl.get(
                                'exclusion_rule_id',
                                'Unknown')}",
                        "description": excl.get("rule_text", "")
                        + "\n"
                        + excl.get("evidence_from_vignette", ""),
                        "confidence": excl.get("confidence_score", 0),
                        "source": "llm",
                    }
                )

        # Get specialty needs
        specialty_needs = []
        for specialty in llm_analysis.get("identified_specialties_needed", []):
            if (
                specialty.get("likelihood_score", 0) > 50
            ):  # Only include likely specialties
                specialty_needs.append(
                    {
                        "name": specialty.get("specialty_name", "Unknown"),
                        "likelihood": specialty.get("likelihood_score", 0),
                        "evidence": specialty.get("supporting_evidence", ""),
                    }
                )

        # Determine if campus is suitable
        is_suitable = len(combined_exclusions) == 0

        # Determine care level needed
        care_level = llm_analysis.get("recommended_care_level", "")
        if not care_level:
            # Fallback to rule-based care level determination
            care_level = determine_care_level(patient_data)

        # Create final analysis
        campus_analysis = {
            "campus_id": campus.campus_id,
            "campus_name": campus.name,
            "is_suitable": is_suitable,
            "exclusions": combined_exclusions,
            "specialty_needs": specialty_needs,
            "recommended_care_level": care_level,
            "confidence": llm_analysis.get("confidence", 0),
            "explanation": llm_analysis.get("explanation", ""),
        }

        return campus_analysis

    def _fallback_campus_analysis(
        self, patient_data: PatientData, campus: HospitalCampus
    ) -> Dict[str, Any]:
        """
        Perform simplified fallback analysis of a campus for a patient.

        Args:
            patient_data: Structured patient data
            campus: Hospital campus to analyze

        Returns:
            Dictionary with campus analysis results
        """
        # Check exclusions using rule-based approach
        exclusions = check_exclusions(patient_data, campus)

        # Determine if campus is suitable
        is_suitable = len(exclusions) == 0

        # Determine care level needed
        care_level = determine_care_level(patient_data)

        # Create simplified analysis
        campus_analysis = {
            "campus_id": campus.campus_id,
            "campus_name": campus.name,
            "is_suitable": is_suitable,
            "exclusions": [
                {
                    "name": excl.name,
                    "description": excl.description,
                    "source": "rule_based",
                }
                for excl in exclusions
            ],
            "specialty_needs": [],  # Can't determine specialty needs in fallback
            "recommended_care_level": care_level,
            "confidence": 70,  # Lower confidence for fallback analysis
            "explanation": "Analysis based on rule-based fallback system due to LLM analysis failure.",
        }

        return campus_analysis

    def _determine_recommended_campus(
        self,
        patient_data: PatientData,
        campuses: List[HospitalCampus],
        campus_analyses: List[Dict[str, Any]],
    ) -> Tuple[Optional[HospitalCampus], str, str]:
        """
        Determine the recommended campus based on analyses.

        Args:
            patient_data: Structured patient data
            campuses: List of candidate campuses
            campus_analyses: List of campus analysis results

        Returns:
            Tuple of (recommended_campus, care_level, explanation)
        """
        # Find suitable campuses
        suitable_campuses = []
        suitable_analyses = []

        for i, analysis in enumerate(campus_analyses):
            if analysis["is_suitable"]:
                suitable_campuses.append(campuses[i])
                suitable_analyses.append(analysis)

        # If no suitable campuses, find the one with fewest exclusions
        if not suitable_campuses:
            min_exclusions = float("inf")
            best_campus_idx = 0

            for i, analysis in enumerate(campus_analyses):
                num_exclusions = len(analysis["exclusions"])
                if num_exclusions < min_exclusions:
                    min_exclusions = num_exclusions
                    best_campus_idx = i

            recommended_campus = campuses[best_campus_idx]
            care_level = campus_analyses[best_campus_idx]["recommended_care_level"]
            explanation = (
                f"No fully suitable campus found. {
                    recommended_campus.name} is recommended as the least "
                + f"problematic option with {min_exclusions} exclusion criteria. "
                + f"Patient requires {care_level} level care."
            )

            return recommended_campus, care_level, explanation

        # If multiple suitable campuses, prioritize based on:
        # 1. Best match for recommended care level
        # 2. Highest confidence
        # 3. First in the list

        care_level = "Regular"  # Default
        for analysis in suitable_analyses:
            if analysis["recommended_care_level"]:
                care_level = analysis["recommended_care_level"]
                break

        # Filter suitable campuses by care level capability
        # (This is simplified - in a real system, you'd match campus capabilities with care level)
        suitable_for_care_level = suitable_campuses

        if suitable_for_care_level:
            # Find the campus with highest confidence
            best_confidence = -1
            best_campus_idx = 0

            for i, campus in enumerate(suitable_for_care_level):
                for j, analysis in enumerate(campus_analyses):
                    if (
                        analysis["campus_id"] == campus.campus_id
                        and analysis["confidence"] > best_confidence
                    ):
                        best_confidence = analysis["confidence"]
                        best_campus_idx = i

            recommended_campus = suitable_for_care_level[best_campus_idx]

            # Find the matching analysis
            matching_analysis = None
            for analysis in campus_analyses:
                if analysis["campus_id"] == recommended_campus.campus_id:
                    matching_analysis = analysis
                    break

            explanation = (
                f"{recommended_campus.name} is recommended as a suitable campus for this patient. "
                + f"Patient requires {care_level} level care. "
                + (
                    matching_analysis["explanation"]
                    if matching_analysis and matching_analysis["explanation"]
                    else ""
                )
            )
        else:
            # Fallback to first suitable campus
            recommended_campus = suitable_campuses[0]
            matching_analysis = suitable_analyses[0]

            explanation = (
                f"{
                    recommended_campus.name} is recommended as a suitable campus for this patient. "
                + f"Patient requires {care_level} level care."
            )

        return recommended_campus, care_level, explanation


# Create singleton instance for application use
llm_interface = LLMInterface()
