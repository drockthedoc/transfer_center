"""
Checks patient data against hospital campus exclusion criteria.

This module provides a function to determine if a patient meets any
predefined exclusion criteria for a given hospital campus based on keywords
found in the patient's chief complaint or clinical history.
"""
from typing import List
from src.core.models import PatientData, HospitalCampus, CampusExclusion

def check_exclusions(patient_data: PatientData, campus: HospitalCampus) -> List[CampusExclusion]:
    """
    Checks if the patient's data meets any of the hospital campus's exclusion criteria.

    Args:
        patient_data: The patient's clinical data.
        campus: The hospital campus data, including its exclusion criteria.

    Returns:
        A list of CampusExclusion objects that the patient meets.
        Returns an empty list if no exclusion criteria are met.
    """
    met_exclusions: List[CampusExclusion] = []
    patient_complaint_lower = patient_data.chief_complaint.lower()
    patient_history_lower = patient_data.clinical_history.lower()

    for exclusion_criterion in campus.exclusions:
        match_found = False
        # Check keywords in chief complaint
        for keyword in exclusion_criterion.affected_keywords_in_complaint:
            if keyword.lower() in patient_complaint_lower:
                met_exclusions.append(exclusion_criterion)
                match_found = True
                break # Move to next exclusion criterion once a match is found for this one
        
        if match_found:
            continue # Already added this criterion, so skip history check for it

        # Check keywords in clinical history
        for keyword in exclusion_criterion.affected_keywords_in_history:
            if keyword.lower() in patient_history_lower:
                met_exclusions.append(exclusion_criterion)
                # No need to set match_found here as we are at the end of checks for this criterion
                break # Move to next exclusion criterion
                
    return met_exclusions
