"""
Exclusion checker component for the Transfer Center decision engine.

This module handles checking if a patient meets any exclusion criteria for a hospital campus.
"""

import logging
from typing import Any, Dict, List, Optional

from src.core.models import CampusExclusion as Exclusion
from src.core.models import HospitalCampus, PatientData

logger = logging.getLogger(__name__)


def check_patient_exclusions(
    patient: PatientData, campus: HospitalCampus
) -> List[Exclusion]:
    """
    Check if a patient meets any exclusion criteria for a hospital campus.

    Args:
        patient: Patient data to check
        campus: Hospital campus to check against

    Returns:
        List of exclusion criteria that apply to the patient (empty if none)
    """
    logger.info(f"Checking exclusions for campus: {campus.name}")

    # Initialize list to hold matching exclusions
    exclusions: List[Exclusion] = []

    # Get patient attributes from extracted data
    care_level = patient.care_level if patient.care_level else "General"
    age = None
    weight = None

    if patient.extracted_data:
        if "demographics" in patient.extracted_data:
            demographics = patient.extracted_data["demographics"]
            if "age" in demographics:
                age = demographics["age"]
            if "weight" in demographics:
                weight = demographics["weight"]

    # Check each exclusion criteria
    for exclusion in campus.exclusions:
        # Age restrictions
        if exclusion.min_age is not None and age is not None:
            if age < exclusion.min_age:
                exclusions.append(exclusion)
                logger.info(
                    f"Patient excluded due to minimum age requirement: {exclusion.name}"
                )
                continue

        if exclusion.max_age is not None and age is not None:
            if age > exclusion.max_age:
                exclusions.append(exclusion)
                logger.info(
                    f"Patient excluded due to maximum age requirement: {exclusion.name}"
                )
                continue

        # Weight restrictions
        if exclusion.min_weight is not None and weight is not None:
            if weight < exclusion.min_weight:
                exclusions.append(exclusion)
                logger.info(
                    f"Patient excluded due to minimum weight requirement: {exclusion.name}"
                )
                continue

        if exclusion.max_weight is not None and weight is not None:
            if weight > exclusion.max_weight:
                exclusions.append(exclusion)
                logger.info(
                    f"Patient excluded due to maximum weight requirement: {exclusion.name}"
                )
                continue

        # Care level restrictions
        if (
            exclusion.excluded_care_levels
            and care_level in exclusion.excluded_care_levels
        ):
            exclusions.append(exclusion)
            logger.info(f"Patient excluded due to care level: {exclusion.name}")
            continue

        # Department/condition exclusions
        if exclusion.excluded_conditions:
            # Check if any patient conditions match excluded conditions
            patient_conditions = patient.care_needs if patient.care_needs else []

            # Also check conditions from extracted data
            if patient.extracted_data and "clinical_info" in patient.extracted_data:
                clinical_info = patient.extracted_data["clinical_info"]
                if "diagnoses" in clinical_info and isinstance(
                    clinical_info["diagnoses"], list
                ):
                    patient_conditions.extend(clinical_info["diagnoses"])

            # Check for matches
            for condition in patient_conditions:
                condition_lower = condition.lower()
                for excluded_condition in exclusion.excluded_conditions:
                    if excluded_condition.lower() in condition_lower:
                        exclusions.append(exclusion)
                        logger.info(
                            f"Patient excluded due to condition: {exclusion.name}"
                        )
                        break

                # Break out of outer loop if exclusion already found
                if exclusions and exclusions[-1] == exclusion:
                    break

    return exclusions
