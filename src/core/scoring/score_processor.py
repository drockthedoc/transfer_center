#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Scoring Processor for Transfer Center

This module integrates the pediatric scoring systems to determine appropriate care levels
and provide comprehensive severity assessments for transfer decisions.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from src.core.models import PatientData
from src.core.scoring.pediatric import (
    calculate_cameo2,
    calculate_chews,
    calculate_pews,
    calculate_prism3,
    calculate_queensland_non_trauma,
    calculate_queensland_trauma,
    calculate_tps,
    calculate_trap,
)

logger = logging.getLogger(__name__)


def extract_vital_signs(patient_data: PatientData) -> Dict[str, Any]:
    """
    Extract vital signs from patient data in a structured format suitable for scoring functions.

    Args:
        patient_data: The patient data object

    Returns:
        Dictionary containing vital sign parameters
    """
    # Initialize vital signs dictionary
    vitals = {}

    # Extract age from extracted_data if available
    age_months = None
    if "age_years" in patient_data.extracted_data:
        age_years = patient_data.extracted_data.get("age_years")
        if age_years is not None:
            try:
                age_months = float(age_years) * 12
            except (ValueError, TypeError):
                pass

    if "age_months" in patient_data.extracted_data:
        age_months_value = patient_data.extracted_data.get("age_months")
        if age_months_value is not None:
            try:
                if age_months is not None:
                    age_months += float(age_months_value)
                else:
                    age_months = float(age_months_value)
            except (ValueError, TypeError):
                pass

    # Get clinical text from either clinical_text or clinical_notes in extracted_data
    clinical_text = patient_data.clinical_text or ""
    if not clinical_text and "clinical_notes" in patient_data.extracted_data:
        clinical_text = patient_data.extracted_data.get("clinical_notes", "")

    # Extract vital signs from extracted_data
    respiratory_rate = None
    if "respiratory_rate" in patient_data.extracted_data:
        try:
            respiratory_rate = float(patient_data.extracted_data["respiratory_rate"])
        except (ValueError, TypeError):
            pass
    elif (
        "vital_signs" in patient_data.extracted_data
        and "respiratory_rate" in patient_data.extracted_data["vital_signs"]
    ):
        try:
            respiratory_rate = float(
                patient_data.extracted_data["vital_signs"]["respiratory_rate"]
            )
        except (ValueError, TypeError):
            pass

    # Extract heart rate
    heart_rate = None
    if "heart_rate" in patient_data.extracted_data:
        try:
            heart_rate = float(patient_data.extracted_data["heart_rate"])
        except (ValueError, TypeError):
            pass
    elif (
        "vital_signs" in patient_data.extracted_data
        and "heart_rate" in patient_data.extracted_data["vital_signs"]
    ):
        try:
            heart_rate = float(patient_data.extracted_data["vital_signs"]["heart_rate"])
        except (ValueError, TypeError):
            pass

    # Extract blood pressure
    systolic_bp = None
    diastolic_bp = None
    if "systolic_bp" in patient_data.extracted_data:
        try:
            systolic_bp = float(patient_data.extracted_data["systolic_bp"])
        except (ValueError, TypeError):
            pass
    elif (
        "vital_signs" in patient_data.extracted_data
        and "systolic_bp" in patient_data.extracted_data["vital_signs"]
    ):
        try:
            systolic_bp = float(
                patient_data.extracted_data["vital_signs"]["systolic_bp"]
            )
        except (ValueError, TypeError):
            pass

    if "diastolic_bp" in patient_data.extracted_data:
        try:
            diastolic_bp = float(patient_data.extracted_data["diastolic_bp"])
        except (ValueError, TypeError):
            pass
    elif (
        "vital_signs" in patient_data.extracted_data
        and "diastolic_bp" in patient_data.extracted_data["vital_signs"]
    ):
        try:
            diastolic_bp = float(
                patient_data.extracted_data["vital_signs"]["diastolic_bp"]
            )
        except (ValueError, TypeError):
            pass

    # Extract oxygen saturation
    oxygen_saturation = None
    if "oxygen_saturation" in patient_data.extracted_data:
        try:
            oxygen_saturation = float(patient_data.extracted_data["oxygen_saturation"])
        except (ValueError, TypeError):
            pass
    elif (
        "vital_signs" in patient_data.extracted_data
        and "oxygen_saturation" in patient_data.extracted_data["vital_signs"]
    ):
        try:
            oxygen_saturation = float(
                patient_data.extracted_data["vital_signs"]["oxygen_saturation"]
            )
        except (ValueError, TypeError):
            pass
    elif (
        "vital_signs" in patient_data.extracted_data
        and "spo2" in patient_data.extracted_data["vital_signs"]
    ):
        try:
            oxygen_saturation = float(
                patient_data.extracted_data["vital_signs"]["spo2"]
            )
        except (ValueError, TypeError):
            pass

    # Extract respiratory effort, oxygen requirement from clinical text
    respiratory_effort = None
    oxygen_requirement = None

    # Simple parsing of respiratory effort
    resp_terms = ["respiratory effort", "work of breathing", "breathing effort"]
    # First check if it's explicitly mentioned in the clinical text
    if (
        "respiratory effort is increased" in clinical_text.lower()
        or "increased work of breathing" in clinical_text.lower()
    ):
        respiratory_effort = "increased"
    else:
        # More generic search
        for term in resp_terms:
            if term in clinical_text.lower():
                text_lower = clinical_text.lower()
                idx = text_lower.find(term)
                if idx >= 0:
                    # Check for common descriptors near the term
                    window_text = text_lower[max(0, idx - 30) : idx + 40]
                    for desc in [
                        "normal",
                        "mild",
                        "moderate",
                        "severe",
                        "increased",
                        "labored",
                    ]:
                        if desc in window_text:
                            respiratory_effort = desc
                            break

    # Simple parsing of oxygen requirement
    oxygen_terms = ["oxygen", "o2", "ventilat", "intubat", "nasal cannula", "high flow"]
    for term in oxygen_terms:
        if term in clinical_text.lower():
            text_lower = clinical_text.lower()
            if "nasal cannula" in text_lower or "low flow" in text_lower:
                oxygen_requirement = "nasal cannula"
            elif "high flow" in text_lower:
                oxygen_requirement = "high flow"
            elif "ventilat" in text_lower or "intubat" in text_lower:
                oxygen_requirement = "ventilator"
            elif "room air" in text_lower or "no oxygen" in text_lower:
                oxygen_requirement = "none"
            break

    # Extract neurological parameters
    gcs = None
    if "gcs" in patient_data.extracted_data:
        try:
            gcs = int(patient_data.extracted_data["gcs"])
        except (ValueError, TypeError):
            pass
    elif (
        "vital_signs" in patient_data.extracted_data
        and "gcs" in patient_data.extracted_data["vital_signs"]
    ):
        try:
            gcs = int(patient_data.extracted_data["vital_signs"]["gcs"])
        except (ValueError, TypeError):
            pass
    else:
        # Try to extract from clinical text
        if "gcs" in clinical_text.lower():
            text_lower = clinical_text.lower()
            idx = text_lower.find("gcs")
            if idx >= 0:
                # Look for a number after "gcs"
                for i in range(idx + 3, min(idx + 20, len(text_lower))):
                    if text_lower[i].isdigit():
                        j = i
                        while j < len(text_lower) and text_lower[j].isdigit():
                            j += 1
                        try:
                            gcs = int(text_lower[i:j])
                            break
                        except ValueError:
                            pass

    # Extract mental status
    mental_status = None
    if "mental_status" in patient_data.extracted_data:
        mental_status = patient_data.extracted_data["mental_status"]
    elif (
        "vital_signs" in patient_data.extracted_data
        and "mental_status" in patient_data.extracted_data["vital_signs"]
    ):
        mental_status = patient_data.extracted_data["vital_signs"]["mental_status"]
    else:
        # Try to extract from clinical text
        status_terms = ["alert", "voice", "pain", "unresponsive", "avpu"]
        for term in status_terms:
            if term in clinical_text.lower():
                text_lower = clinical_text.lower()
                if "alert" in text_lower:
                    mental_status = "alert"
                elif "voice" in text_lower or "responds to voice" in text_lower:
                    mental_status = "voice"
                elif "pain" in text_lower or "responds to pain" in text_lower:
                    mental_status = "pain"
                elif "unresponsive" in text_lower or "unconscious" in text_lower:
                    mental_status = "unresponsive"
                break

    # Extract capillary refill
    capillary_refill = None
    if "capillary_refill" in patient_data.extracted_data:
        try:
            capillary_refill = float(patient_data.extracted_data["capillary_refill"])
        except (ValueError, TypeError):
            pass
    elif (
        "vital_signs" in patient_data.extracted_data
        and "capillary_refill" in patient_data.extracted_data["vital_signs"]
    ):
        try:
            capillary_refill = float(
                patient_data.extracted_data["vital_signs"]["capillary_refill"]
            )
        except (ValueError, TypeError):
            pass
    else:
        # Try to extract from clinical text
        if "capillary refill" in clinical_text.lower():
            text_lower = clinical_text.lower()
            idx = text_lower.find("capillary refill")
            if idx >= 0:
                # Look for a number after "capillary refill"
                for i in range(idx + 15, min(idx + 30, len(text_lower))):
                    if text_lower[i].isdigit() or text_lower[i] == ".":
                        j = i
                        while j < len(text_lower) and (
                            text_lower[j].isdigit() or text_lower[j] == "."
                        ):
                            j += 1
                        try:
                            capillary_refill = float(text_lower[i:j])
                            break
                        except ValueError:
                            pass

    # Build and return the vitals dictionary
    weight_kg = None
    if "weight_kg" in patient_data.extracted_data:
        try:
            weight_kg = float(patient_data.extracted_data["weight_kg"])
        except (ValueError, TypeError):
            pass

    vitals = {
        "age_months": age_months,
        "respiratory_rate": respiratory_rate,
        "respiratory_effort": respiratory_effort,
        "oxygen_requirement": oxygen_requirement,
        "oxygen_saturation": oxygen_saturation,
        "heart_rate": heart_rate,
        "systolic_bp": systolic_bp,
        "diastolic_bp": diastolic_bp,
        "gcs": gcs,
        "mental_status": mental_status,
        "capillary_refill": capillary_refill,
        "weight_kg": weight_kg,
    }

    return vitals


def determine_trauma_status(patient_data: PatientData) -> bool:
    """
    Determine if the patient is a trauma case based on clinical text.

    Args:
        patient_data: The patient data object

    Returns:
        True if trauma is detected, False otherwise
    """
    clinical_text = patient_data.clinical_text or ""
    if not clinical_text and "clinical_notes" in patient_data.extracted_data:
        clinical_text = patient_data.extracted_data.get("clinical_notes", "")

    if not clinical_text:
        return False

    # Keywords that suggest trauma
    trauma_keywords = [
        "trauma",
        "accident",
        "injury",
        "fracture",
        "collision",
        "fall",
        "mvc",
        "motor vehicle",
        "crash",
        "assault",
        "burn",
        "blast",
        "gunshot",
        "stab",
        "penetrating",
        "blunt",
        "wound",
    ]

    text_lower = clinical_text.lower()

    # Check for trauma keywords
    for keyword in trauma_keywords:
        if keyword in text_lower:
            return True

    return False


def calculate_all_scores(patient_data: PatientData) -> Dict[str, Any]:
    """
    Calculate all applicable pediatric severity scores for a patient.

    Args:
        patient_data: The patient data object

    Returns:
        Dictionary containing all calculated scores and their details
    """
    # Extract structured vital signs
    vitals = extract_vital_signs(patient_data)

    # Determine if trauma case
    is_trauma = determine_trauma_status(patient_data)

    # Initialize results
    scores = {}

    # Calculate PEWS score
    pews_result = calculate_pews(
        age_months=vitals["age_months"],
        respiratory_rate=vitals["respiratory_rate"],
        respiratory_effort=vitals["respiratory_effort"],
        oxygen_requirement=vitals["oxygen_requirement"],
        heart_rate=vitals["heart_rate"],
        capillary_refill=vitals["capillary_refill"],
        behavior=vitals["mental_status"],
    )
    scores["pews"] = pews_result

    # Calculate TRAP score for transport risk
    trap_result = calculate_trap(
        respiratory_support=vitals["oxygen_requirement"],
        respiratory_rate=vitals["respiratory_rate"],
        work_of_breathing=vitals["respiratory_effort"],
        oxygen_saturation=vitals["oxygen_saturation"],
        hemodynamic_stability=None,  # Not directly available
        blood_pressure=vitals["systolic_bp"],
        heart_rate=vitals["heart_rate"],
        neuro_status=vitals["mental_status"],
        gcs=vitals["gcs"],
        access_difficulty=None,  # Not directly available
        age_months=vitals["age_months"],
    )
    scores["trap"] = trap_result

    # Calculate CHEWS score
    chews_result = calculate_chews(
        respiratory_rate=vitals["respiratory_rate"],
        respiratory_effort=vitals["respiratory_effort"],
        heart_rate=vitals["heart_rate"],
        systolic_bp=vitals["systolic_bp"],
        capillary_refill=vitals["capillary_refill"],
        oxygen_therapy=vitals["oxygen_requirement"],
        oxygen_saturation=vitals["oxygen_saturation"],
        age_months=vitals["age_months"],
    )
    scores["chews"] = chews_result

    # Calculate TPS score for transport physiology
    tps_result = calculate_tps(
        respiratory_status=vitals["respiratory_effort"],
        circulation_status=None,  # Not directly available
        neurologic_status=vitals["mental_status"],
    )
    scores["tps"] = tps_result

    # Calculate Queensland scores based on trauma status
    if is_trauma:
        # For trauma cases
        qld_result = calculate_queensland_trauma(
            mechanism=None,  # Need more detailed parsing
            consciousness=vitals["mental_status"],
            airway=None,  # Need more detailed parsing
            breathing=vitals["respiratory_effort"],
            circulation=None,  # Need more detailed parsing
        )
        scores["queensland_trauma"] = qld_result
    else:
        # For non-trauma cases
        qld_result = calculate_queensland_non_trauma(
            resp_rate=vitals["respiratory_rate"],
            HR=vitals["heart_rate"],
            mental_status=vitals["mental_status"],
            SpO2=vitals["oxygen_saturation"],
            age_months=vitals["age_months"],
        )
        scores["queensland_non_trauma"] = qld_result

    # Extract labs if available for PRISM III
    labs = {}
    clinical_text = patient_data.clinical_text or ""
    if clinical_text:
        # This would need more sophisticated parsing in a real implementation
        # For demonstration, we'll leave labs empty
        pass

    # Determine ventilation status
    ventilated = False
    if vitals["oxygen_requirement"] == "ventilator":
        ventilated = True

    # Calculate PRISM III if sufficient data
    vitals_dict = {
        "systolic_bp": vitals["systolic_bp"],
        "heart_rate": vitals["heart_rate"],
        "gcs": vitals["gcs"],
        "pupils": None,  # Not directly available
        "temperature": None,  # Not directly available
    }

    prism_result = calculate_prism3(
        vitals=vitals_dict,
        labs=labs,
        age_months=vitals["age_months"],
        ventilated=ventilated,
    )
    scores["prism3"] = prism_result

    return scores


def determine_care_level(scores: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Determine appropriate care level based on severity scores.

    Args:
        scores: Dictionary of calculated severity scores

    Returns:
        Tuple of (care_levels, justifications)
    """
    care_levels = []
    justifications = []

    # Check PEWS score
    if scores["pews"] != "N/A" and isinstance(scores["pews"]["score"], int):
        pews_score = scores["pews"]["score"]
        if pews_score >= 7:
            care_levels.append("PICU")
            justifications.append(f"PEWS score {pews_score} (Critical Risk)")
        elif pews_score >= 5:
            care_levels.append("PICU")
            justifications.append(f"PEWS score {pews_score} (High Risk)")
        elif pews_score >= 3:
            care_levels.append("Intermediate")
            justifications.append(f"PEWS score {pews_score} (Medium Risk)")

    # Check TRAP score for transport considerations
    if scores["trap"] != "N/A" and isinstance(scores["trap"]["score"], int):
        trap_score = scores["trap"]["score"]
        trap_risk = scores["trap"]["risk_level"]
        if "Critical" in trap_risk or "High" in trap_risk:
            care_levels.append("PICU")
            justifications.append(f"TRAP score {trap_score} ({trap_risk})")

    # Check CHEWS score
    if scores["chews"] != "N/A" and isinstance(scores["chews"]["score"], int):
        chews_score = scores["chews"]["score"]
        if chews_score >= 7:
            care_levels.append("PICU")
            justifications.append(f"CHEWS score {chews_score} (Critical Alert Level)")
        elif chews_score >= 5:
            care_levels.append("PICU")
            justifications.append(f"CHEWS score {chews_score} (High Alert Level)")
        elif chews_score >= 3:
            care_levels.append("Intermediate")
            justifications.append(f"CHEWS score {chews_score} (Medium Alert Level)")

    # Check PRISM III score
    if scores["prism3"] != "N/A" and isinstance(scores["prism3"]["score"], int):
        prism_score = scores["prism3"]["score"]
        if prism_score >= 10:
            care_levels.append("PICU")
            justifications.append(
                f"PRISM III score {prism_score} (High mortality risk)"
            )

    # Check Queensland score
    if (
        "queensland_trauma" in scores
        and scores["queensland_trauma"] != "N/A"
        and isinstance(scores["queensland_trauma"]["score"], int)
    ):
        qld_score = scores["queensland_trauma"]["score"]
        if qld_score >= 9:
            care_levels.append("PICU")
            justifications.append(
                f"Queensland Trauma score {qld_score} (High/Critical Risk)"
            )
    elif (
        "queensland_non_trauma" in scores
        and scores["queensland_non_trauma"] != "N/A"
        and isinstance(scores["queensland_non_trauma"]["score"], int)
    ):
        qld_score = scores["queensland_non_trauma"]["score"]
        if qld_score >= 7:
            care_levels.append("PICU")
            justifications.append(
                f"Queensland Non-Trauma score {qld_score} (High/Critical Risk)"
            )

    # Determine NICU need based on age and scores
    if scores["pews"] != "N/A" and "age_months" in scores["pews"].get("vitals", {}):
        age_months = scores["pews"]["vitals"]["age_months"]
        if age_months is not None and age_months < 1:  # Neonate
            care_levels.append("NICU")
            justifications.append(f"Neonate (age < 1 month)")

    # If no specific care level determined but scores indicate concern
    if not care_levels:
        # Default to general care but check for any elevated scores
        any_elevated = False
        if (
            scores["pews"] != "N/A"
            and isinstance(scores["pews"]["score"], int)
            and scores["pews"]["score"] >= 2
        ):
            any_elevated = True

        if any_elevated:
            care_levels.append("Intermediate")
            justifications.append("Moderately elevated severity scores")
        else:
            care_levels.append("General")
            justifications.append("Low severity scores across all measures")

    # Remove duplicates while preserving order
    unique_care_levels = []
    for level in care_levels:
        if level not in unique_care_levels:
            unique_care_levels.append(level)

    return unique_care_levels, justifications


def process_patient_scores(patient_data: PatientData) -> Dict[str, Any]:
    """
    Process a patient's data to calculate scores and determine care level.

    Args:
        patient_data: The patient data object

    Returns:
        Dictionary with scores, care level recommendations, and justifications
    """
    # Calculate all applicable scores
    scores = calculate_all_scores(patient_data)

    # Determine care level based on scores
    care_levels, justifications = determine_care_level(scores)

    # Compile results
    result = {
        "scores": scores,
        "recommended_care_levels": care_levels,
        "justifications": justifications,
    }

    return result
