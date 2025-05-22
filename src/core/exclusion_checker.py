"""
Checks patient data against hospital campus exclusion criteria.

This module provides functions to determine if a patient meets any
predefined exclusion criteria for a given hospital campus based on
structured exclusion criteria from JSON files.
"""
import os
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from src.core.models import PatientData, HospitalCampus, CampusExclusion

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to exclusion criteria JSON file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXCLUSION_FILE = os.path.join(BASE_DIR, "data", "exclusion_criteria_clean.json")

# Cache for loaded exclusion criteria
_exclusion_criteria_cache = None

def load_exclusion_criteria() -> Dict[str, Any]:
    """
    Loads the exclusion criteria from the JSON file.
    Uses a cache to avoid repeatedly reading the file.
    
    Returns:
        Dictionary containing the structured exclusion criteria.
    """
    global _exclusion_criteria_cache
    
    if _exclusion_criteria_cache is not None:
        return _exclusion_criteria_cache
    
    try:
        if os.path.exists(EXCLUSION_FILE):
            with open(EXCLUSION_FILE, 'r') as f:
                _exclusion_criteria_cache = json.load(f)
            logger.info(f"Loaded exclusion criteria from {EXCLUSION_FILE}")
            return _exclusion_criteria_cache
        else:
            logger.warning(f"Exclusion criteria file not found: {EXCLUSION_FILE}")
            return {"campuses": {}}
    except Exception as e:
        logger.error(f"Error loading exclusion criteria: {e}")
        return {"campuses": {}}

def matches_age_restriction(patient_age: Optional[int], restrictions: Dict[str, int]) -> Tuple[bool, str]:
    """
    Check if a patient's age matches the restriction criteria.
    
    Args:
        patient_age: The patient's age in years (or None if unknown)
        restrictions: Dictionary with 'minimum' and/or 'maximum' age limits
        
    Returns:
        Tuple of (matches_restriction, explanation)
    """
    if patient_age is None:
        return False, "Patient age unknown"
    
    if 'minimum' in restrictions and patient_age < restrictions['minimum']:
        return True, f"Patient age {patient_age} is below minimum age {restrictions['minimum']}"
    
    if 'maximum' in restrictions and patient_age > restrictions['maximum']:
        return True, f"Patient age {patient_age} exceeds maximum age {restrictions['maximum']}"
    
    return False, ""

def matches_weight_restriction(patient_weight: Optional[float], restrictions: Dict[str, float]) -> Tuple[bool, str]:
    """
    Check if a patient's weight matches the restriction criteria.
    
    Args:
        patient_weight: The patient's weight in kg (or None if unknown)
        restrictions: Dictionary with 'minimum' and/or 'maximum' weight limits
        
    Returns:
        Tuple of (matches_restriction, explanation)
    """
    if patient_weight is None:
        return False, "Patient weight unknown"
    
    if 'minimum' in restrictions and patient_weight < restrictions['minimum']:
        return True, f"Patient weight {patient_weight:.1f}kg is below minimum weight {restrictions['minimum']:.1f}kg"
    
    if 'maximum' in restrictions and patient_weight > restrictions['maximum']:
        return True, f"Patient weight {patient_weight:.1f}kg exceeds maximum weight {restrictions['maximum']:.1f}kg"
    
    return False, ""

def check_keyword_match(text: str, keywords: List[str]) -> bool:
    """
    Check if any keyword appears in the text.
    
    Args:
        text: The text to search in
        keywords: List of keywords to search for
        
    Returns:
        True if any keyword is found in the text
    """
    if not text or not keywords:
        return False
    
    text = text.lower()
    for keyword in keywords:
        if keyword.lower() in text:
            return True
    
    return False

def check_specialization_needs(patient_data: PatientData, campus_data: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    Check if patient has specialization needs that are excluded at this campus.
    
    Args:
        patient_data: The patient's data
        campus_data: Campus exclusion criteria data
        
    Returns:
        List of (department, reason) tuples for matched exclusions
    """
    matched_exclusions = []
    
    # Combine patient text for searching
    patient_text = f"{patient_data.chief_complaint} {patient_data.clinical_history}".lower()
    
    # Check each department's exclusions
    for dept, dept_data in campus_data.get('departments', {}).items():
        for exclusion in dept_data.get('exclusions', []):
            # Look for direct keyword matches
            exclusion_lower = exclusion.lower()
            
            # Extract key phrases that might indicate this exclusion applies
            phrases = re.split(r'[,;.]', exclusion_lower)
            
            for phrase in phrases:
                phrase = phrase.strip()
                if len(phrase) > 5 and phrase in patient_text:
                    matched_exclusions.append((dept, f"Matched exclusion criterion: {exclusion}"))
                    break
        
        # Check for condition matches
        for condition in dept_data.get('conditions', []):
            condition_keywords = [
                condition,
                *[c for c in condition.split('_')],  # Split compound conditions
                *[c for c in condition.split('-')]   # Split hyphenated conditions
            ]
            
            if check_keyword_match(patient_text, condition_keywords):
                matched_exclusions.append((dept, f"Patient condition matches excluded {condition} in {dept} department"))
    
    return matched_exclusions

def check_department_exclusions(patient_data: PatientData, 
department_data: Dict[str, Any], department_name: str) -> List[CampusExclusion]:
    """
    Check if the patient matches any exclusion criteria for a specific department.
    
    Args:
        patient_data: The patient's data
        department_data: Department exclusion criteria data
        department_name: Name of the department being checked
        
    Returns:
        List of CampusExclusion objects for matched exclusions
    """
    met_exclusions = []
    patient_text = f"{patient_data.chief_complaint} {patient_data.clinical_history}".lower()
    
    # Extract specialty needs from patient text
    for condition in department_data.get('conditions', []):
        # Don't just check for the condition name, but also related terms
        condition_terms = [condition]
        # Add related terms for common conditions
        if condition == 'cardiac':
            condition_terms.extend(['heart', 'cardiac', 'cardio', 'chest pain'])
        elif condition == 'respiratory':
            condition_terms.extend(['breathing', 'breath', 'respiratory', 'lungs', 'pulmonary'])
        elif condition == 'neurological':
            condition_terms.extend(['brain', 'neuro', 'stroke', 'seizure', 'mental status'])
        
        # Check if any condition terms appear in the patient text
        if any(term in patient_text for term in condition_terms):
            # Check exclusions first
            for exclusion in department_data.get('exclusions', []):
                # Extract key phrases from the exclusion
                key_phrases = [phrase.strip() for phrase in re.split(r'[,;.]', exclusion.lower()) 
                               if len(phrase.strip()) > 5]
                
                # Check if any key phrase appears in the patient text
                for phrase in key_phrases:
                    if phrase in patient_text:
                        met_exclusions.append(
                            CampusExclusion(
                                name=f"{department_name.title()} Exclusion",
                                description=f"Patient with {condition} condition matches exclusion: {exclusion}",
                                affected_keywords_in_complaint=[condition],
                                affected_keywords_in_history=[condition]
                            )
                        )
                        break
            
            # If no specific exclusion matched but the condition is present,
            # add a general note about the department's specialty needs
            if not any(excl.name.startswith(f"{department_name.title()} Exclusion") for excl in met_exclusions):
                # Check if there are any notes about clinical team decisions
                if 'clinical_team_decision' in department_data or 'ac_exclusion_picu_accept' in department_data:
                    met_exclusions.append(
                        CampusExclusion(
                            name=f"{department_name.title()} Special Case",
                            description=(f"Patient with {condition} condition may require clinical team review " + 
                                        f"or special consideration for this campus."),
                            affected_keywords_in_complaint=[condition],
                            affected_keywords_in_history=[condition]
                        )
                    )
    
    return met_exclusions

def check_exclusions(patient_data: PatientData, campus: HospitalCampus) -> List[CampusExclusion]:
    """
    Checks if the patient's data meets any of the hospital campus's exclusion criteria
    using the structured JSON data.

    Args:
        patient_data: The patient's clinical data.
        campus: The hospital campus data.

    Returns:
        A list of CampusExclusion objects that the patient meets.
        Returns an empty list if no exclusion criteria are met.
    """
    met_exclusions: List[CampusExclusion] = []
    
    # Load exclusion criteria
    criteria = load_exclusion_criteria()
    
    # Find the campus in the criteria (use a case-insensitive match)
    campus_id = campus.campus_id.lower() if campus.campus_id else ""
    campus_name = campus.name.lower() if campus.name else ""
    
    # Try to match campus by ID or name
    campus_key = None
    for key in criteria.get('campuses', {}).keys():
        campus_display = criteria['campuses'][key].get('display_name', '').lower()
        if (key.lower() in campus_id or 
            key.lower() in campus_name or
            campus_id in key.lower() or
            campus_name in key.lower() or
            campus_id in campus_display or
            campus_name in campus_display):
            campus_key = key
            break
    
    if not campus_key:
        logger.warning(f"No exclusion criteria found for campus: {campus.name} (ID: {campus.campus_id})")
        return met_exclusions
    
    campus_criteria = criteria['campuses'][campus_key]
    
    # Check age restrictions
    if campus_criteria.get('age_restrictions') and hasattr(patient_data, 'age'):
        matches, reason = matches_age_restriction(patient_data.age, campus_criteria['age_restrictions'])
        if matches:
            met_exclusions.append(
                CampusExclusion(
                    name=f"Age Restriction",
                    description=reason,
                    affected_keywords_in_complaint=["age"],
                    affected_keywords_in_history=["age"]
                )
            )
    
    # Check weight restrictions
    if campus_criteria.get('weight_restrictions') and hasattr(patient_data, 'weight_kg'):
        matches, reason = matches_weight_restriction(patient_data.weight_kg, campus_criteria['weight_restrictions'])
        if matches:
            met_exclusions.append(
                CampusExclusion(
                    name=f"Weight Restriction",
                    description=reason,
                    affected_keywords_in_complaint=["weight"],
                    affected_keywords_in_history=["weight"]
                )
            )
    
    # Check general exclusions
    patient_text = f"{patient_data.chief_complaint} {patient_data.clinical_history}".lower()
    for exclusion in campus_criteria.get('general_exclusions', []):
        exclusion_lower = exclusion.lower()
        # Extract key phrases from the exclusion text
        key_phrases = [phrase.strip() for phrase in re.split(r'[,;.]', exclusion_lower) if len(phrase.strip()) > 5]
        
        # Check for phrase matches
        for phrase in key_phrases:
            if phrase in patient_text:
                met_exclusions.append(
                    CampusExclusion(
                        name=f"General Exclusion",
                        description=f"Matched general exclusion: {exclusion}",
                        affected_keywords_in_complaint=[phrase],
                        affected_keywords_in_history=[phrase]
                    )
                )
                break
    
    # Check department-specific exclusions
    for dept_name, dept_data in campus_criteria.get('departments', {}).items():
        dept_exclusions = check_department_exclusions(patient_data, dept_data, dept_name)
        met_exclusions.extend(dept_exclusions)
    
    # Add special notes for context
    if met_exclusions and 'campus_notes' in campus_criteria:
        for note_key, note_text in campus_criteria['campus_notes'].items():
            if note_key in ['ac_exclusion_picu_accept', 'community_exclusion', 'clinical_team'] and len(met_exclusions) > 0:
                # Only add the first relevant note to avoid cluttering
                if not any(excl.name == "Campus Note" for excl in met_exclusions):
                    met_exclusions.append(
                        CampusExclusion(
                            name="Campus Note",
                            description=note_text,
                            affected_keywords_in_complaint=[],
                            affected_keywords_in_history=[]
                        )
                    )
    
    return met_exclusions
