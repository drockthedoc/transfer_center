#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Pediatric Severity Scoring Systems

This module implements validated clinical scoring systems used in pediatric
care for assessing severity, risk, and appropriate level of care.

Each scoring system is implemented according to published clinical guidelines
and validated research, with appropriate thresholds and interpretations.
"""

import logging
from typing import Dict, List, Optional, Tuple, Union, Any

# Import utility functions and constants from the new location
from src.core.scoring.utils import (
    get_age_based_ranges, safe_get_from_map, check_missing_params, create_na_response, 
    normalize_to_risk_level, parse_numeric_or_map,
    RESPIRATORY_EFFORT_MAP, OXYGEN_THERAPY_MAP, MENTAL_STATUS_MAP, BEHAVIOR_MAP, HEMODYNAMIC_MAP
)

logger = logging.getLogger(__name__)

__all__ = [
    'calculate_pews',
    'calculate_trap',
    'calculate_cameo2',
    'calculate_prism3',
    'calculate_queensland_non_trauma',
    'calculate_queensland_trauma',
    'calculate_tps',
    'calculate_chews',
]

# PEWS - Pediatric Early Warning Score

def calculate_pews(age_months=None, respiratory_rate=None, respiratory_effort=None, oxygen_requirement=None, 
                   heart_rate=None, capillary_refill=None, behavior=None):
    """
    Calculate the Pediatric Early Warning Score (PEWS)
    
    Args:
        age_months: Age in months
        respiratory_rate: Breaths per minute
        respiratory_effort: String descriptor ('normal', 'mild', 'moderate', 'severe')
        oxygen_requirement: String descriptor ('none', 'low', 'medium', 'high')
        heart_rate: Beats per minute
        capillary_refill: Time in seconds
        behavior: String descriptor ('playing', 'sleeping', 'irritable', 'lethargic', 'unresponsive')
        
    Returns:
        Dictionary with score, interpretation, and subscores. Returns 'N/A' for score and subscores
        if required parameters are missing.
    """
    # Check for required parameters
    required_params = {
        'respiratory_rate': respiratory_rate,
        'respiratory_effort': respiratory_effort,
        'heart_rate': heart_rate,
        'behavior': behavior
    }
    
    missing_params = [param for param, value in required_params.items() if value is None]
    if missing_params:
        return create_na_response(
            "PEWS", missing_params, 
            ["respiratory", "cardiovascular", "behavior"],
            include_interpretation=True, include_action=True
        )
    
    # Check if age is missing
    if age_months is None:
        return create_na_response(
            "PEWS", ["age_months"], 
            ["respiratory", "cardiovascular", "behavior"],
            include_interpretation=True, include_action=True
        )
    
    # Get reference ranges for this age
    ranges = get_age_based_ranges(age_months)
    
    # Initialize subscores
    respiratory_subscore = 0
    cardiovascular_subscore = 0
    behavior_subscore = 0
    
    # Score respiratory parameters
    rr_min, rr_max = ranges['respiratory_rate']
    
    # Respiratory rate scoring
    if respiratory_rate < rr_min - 5:
        respiratory_subscore += 1
    elif respiratory_rate < rr_min - 10:
        respiratory_subscore += 2
    elif respiratory_rate > rr_max + 5:
        respiratory_subscore += 1
    elif respiratory_rate > rr_max + 10:
        respiratory_subscore += 2
    elif respiratory_rate > rr_max + 15:
        respiratory_subscore += 3
        
    # Respiratory effort scoring
    respiratory_subscore += safe_get_from_map(respiratory_effort, RESPIRATORY_EFFORT_MAP)
    
    # Oxygen requirement scoring
    oxygen_score = safe_get_from_map(oxygen_requirement, OXYGEN_THERAPY_MAP)
    respiratory_subscore = max(respiratory_subscore, oxygen_score)
    
    # Score cardiovascular parameters
    hr_min, hr_max = ranges['heart_rate']
    
    # Heart rate scoring
    if heart_rate < hr_min - 10:
        cardiovascular_subscore += 1
    elif heart_rate < hr_min - 20:
        cardiovascular_subscore += 2
    elif heart_rate > hr_max + 20:
        cardiovascular_subscore += 1
    elif heart_rate > hr_max + 30:
        cardiovascular_subscore += 3
        
    # Capillary refill scoring - handle None values
    if capillary_refill is not None:
        if capillary_refill >= 3:
            cardiovascular_subscore += 2
        elif capillary_refill >= 2:
            cardiovascular_subscore += 1
    
    # Score behavior/neurological parameters
    behavior_subscore = safe_get_from_map(behavior, BEHAVIOR_MAP)
    
    # Combine subscores
    total_score = respiratory_subscore + cardiovascular_subscore + behavior_subscore
    
    # Determine interpretation based on total score
    if total_score <= 2:
        interpretation = "Low Risk: Routine care"
        action = "Continue routine monitoring"
    elif total_score <= 4:
        interpretation = "Medium Risk: Increased surveillance"
        action = "Increase frequency of vital sign monitoring; consider notification of medical team"
    elif total_score <= 6:
        interpretation = "High Risk: Medical review needed"
        action = "Notify medical team now; consider PICU consult"
    else:  # score > 6
        interpretation = "Critical Risk: Immediate intervention"
        action = "Immediate medical team review; PICU consult/transfer indicated"
    
    return {
        "score": total_score,
        "interpretation": interpretation,
        "action": action,
        "subscores": {
            "respiratory": respiratory_subscore,
            "cardiovascular": cardiovascular_subscore,
            "behavior": behavior_subscore
        },
        "normal_ranges": {
            "heart_rate": f"{hr_min}-{hr_max} bpm",
            "respiratory_rate": f"{rr_min}-{rr_max} bpm"
        }
    }


def calculate_trap(respiratory_support=None, respiratory_rate=None, work_of_breathing=None, 
                   oxygen_saturation=None, hemodynamic_stability=None, 
                   blood_pressure=None, heart_rate=None, neuro_status=None,
                   gcs=None, access_difficulty=None, age_months=None):
    """
    Calculate the Transport Risk Assessment in Pediatrics (TRAP) Score
    
    The TRAP score helps assess the risk of deterioration during inter-facility transport.
    It evaluates respiratory, hemodynamic, neurologic, and access domains.
    
    Args:
        respiratory_support: Level of respiratory support ('none', 'nasal cannula', 'high flow', 'ventilated')
        respiratory_rate: Breaths per minute
        work_of_breathing: Description of work of breathing ('normal', 'increased', etc.)
        oxygen_saturation: SpO2 percentage
        hemodynamic_stability: Description of hemodynamic status ('stable', 'compensated', 'unstable')
        blood_pressure: Systolic blood pressure in mmHg
        heart_rate: Beats per minute
        neuro_status: Description of neurological status ('alert', 'voice', 'pain', 'unresponsive')
        gcs: Glasgow Coma Scale score (3-15)
        access_difficulty: Difficulty of vascular access ('easy', 'moderate', 'difficult')
        age_months: Age in months (for age-appropriate vital sign thresholds)
        
    Returns:
        Dictionary with overall risk level, subscores by domain, and recommended transport team.
        Returns 'N/A' for risk level and all subscores if required parameters are missing.
    """
    # Check for critical parameters (at least one from each domain)
    respiratory_domain = {
        'respiratory_support': respiratory_support,
        'respiratory_rate': respiratory_rate,
        'work_of_breathing': work_of_breathing,
        'oxygen_saturation': oxygen_saturation
    }
    
    hemodynamic_domain = {
        'hemodynamic_stability': hemodynamic_stability,
        'blood_pressure': blood_pressure,
        'heart_rate': heart_rate
    }
    
    neuro_domain = {
        'neuro_status': neuro_status,
        'gcs': gcs
    }
    
    # Create a domain validity check
    has_respiratory = any(v is not None for v in respiratory_domain.values())
    has_hemodynamic = any(v is not None for v in hemodynamic_domain.values())
    has_neuro = any(v is not None for v in neuro_domain.values())
    
    # All three domains must have at least one parameter
    missing_domains = []
    if not has_respiratory:
        missing_domains.append("respiratory")
    if not has_hemodynamic:
        missing_domains.append("hemodynamic")
    if not has_neuro:
        missing_domains.append("neuro")
    
    # If any domain is completely missing, return N/A
    if missing_domains:
        subscore_keys = ["respiratory", "hemodynamic", "neurologic", "access"]
        return create_na_response(
            "TRAP", missing_domains, subscore_keys,
            include_interpretation=False, include_action=True
        )
    
    # If age is missing for reference ranges, return N/A
    if age_months is None and (respiratory_rate is not None or heart_rate is not None):
        return create_na_response(
            "TRAP", ["age_months"], 
            ["respiratory", "hemodynamic", "neurologic", "access"],
            include_interpretation=False, include_action=True
        )
    
    # Initialize domain scores
    respiratory_score = 0
    hemodynamic_score = 0
    neurologic_score = 0
    access_score = 0
    
    # Get reference ranges if age is provided
    ranges = None
    if age_months is not None:
        ranges = get_age_based_ranges(age_months)
    
    # Score respiratory domain
    if respiratory_support is not None:
        respiratory_score = max(respiratory_score, safe_get_from_map(respiratory_support, OXYGEN_THERAPY_MAP))
    
    if work_of_breathing is not None:
        respiratory_score = max(respiratory_score, safe_get_from_map(work_of_breathing, RESPIRATORY_EFFORT_MAP))
    
    if oxygen_saturation is not None:
        if oxygen_saturation < 90:
            respiratory_score = max(respiratory_score, 3)
        elif oxygen_saturation < 94:
            respiratory_score = max(respiratory_score, 2)
        elif oxygen_saturation < 97:
            respiratory_score = max(respiratory_score, 1)
    
    if respiratory_rate is not None and ranges:
        rr_min, rr_max = ranges['respiratory_rate']
        if respiratory_rate < rr_min - 10 or respiratory_rate > rr_max + 20:
            respiratory_score = max(respiratory_score, 3)
        elif respiratory_rate < rr_min - 5 or respiratory_rate > rr_max + 10:
            respiratory_score = max(respiratory_score, 2)
        elif respiratory_rate < rr_min or respiratory_rate > rr_max + 5:
            respiratory_score = max(respiratory_score, 1)
    
    # Score hemodynamic domain
    if hemodynamic_stability is not None:
        hemodynamic_score = max(hemodynamic_score, safe_get_from_map(hemodynamic_stability, HEMODYNAMIC_MAP))
    
    if heart_rate is not None and ranges:
        hr_min, hr_max = ranges['heart_rate']
        if heart_rate < hr_min - 20 or heart_rate > hr_max + 30:
            hemodynamic_score = max(hemodynamic_score, 3)
        elif heart_rate < hr_min - 10 or heart_rate > hr_max + 20:
            hemodynamic_score = max(hemodynamic_score, 2)
        elif heart_rate < hr_min or heart_rate > hr_max + 10:
            hemodynamic_score = max(hemodynamic_score, 1)
    
    if blood_pressure is not None and age_months is not None:
        # Simplified age-based normal SBP: 70 + (2 × age in years)
        normal_sbp = 70 + (2 * (age_months / 12))
        if blood_pressure < normal_sbp - 20:
            hemodynamic_score = max(hemodynamic_score, 3)
        elif blood_pressure < normal_sbp - 10:
            hemodynamic_score = max(hemodynamic_score, 2)
        elif blood_pressure < normal_sbp - 5:
            hemodynamic_score = max(hemodynamic_score, 1)
    
    # Score neurologic domain
    if neuro_status is not None:
        neurologic_score = max(neurologic_score, safe_get_from_map(neuro_status, MENTAL_STATUS_MAP))
    
    if gcs is not None:
        try:
            gcs_val = int(gcs)
            if gcs_val <= 8:
                neurologic_score = max(neurologic_score, 3)
            elif gcs_val <= 12:
                neurologic_score = max(neurologic_score, 2)
            elif gcs_val <= 14:
                neurologic_score = max(neurologic_score, 1)
        except (ValueError, TypeError):
            pass  # Skip GCS if it's not a valid number
    
    # Score access difficulty
    if access_difficulty is not None:
        access_map = {
            'easy': 0,
            'normal': 0,
            'routine': 0,
            'moderate': 1,
            'challenging': 1,
            'difficult': 2,
            'very difficult': 3,
            'central': 3,
            'io': 3,
            'intraosseous': 3
        }
        access_score = access_map.get(str(access_difficulty).lower(), 0)
    
    # Calculate maximum domain score and overall risk level
    max_domain_score = max(respiratory_score, hemodynamic_score, neurologic_score)
    
    # Add access difficulty as a modifier
    if max_domain_score >= 2 and access_score >= 2:
        max_domain_score += 1  # Increase risk level if unstable with difficult access
    
    # Determine risk level and transport team recommendation
    trap_thresholds = [
        (0, "Low Risk", "Standard transport team"),
        (1, "Medium Risk", "Consider advanced care providers"),
        (2, "High Risk", "Advanced care transport team required"),
        (3, "Critical Risk", "Critical care transport team required with physician consideration")
    ]
    
    risk_level, transport_recommendation = normalize_to_risk_level(max_domain_score, trap_thresholds)
    
    return {
        "score": max_domain_score,
        "risk_level": risk_level,
        "transport_recommendation": transport_recommendation,
        "subscores": {
            "respiratory": respiratory_score,
            "hemodynamic": hemodynamic_score,
            "neurologic": neurologic_score,
            "access": access_score
        }
    }


def calculate_cameo2(physiologic_instability=None, respiratory_support=None, oxygen_requirement=None, 
                     cardiovascular_support=None, vitals_frequency=None, intervention_level=None, 
                     invasive_lines=None, medication_complexity=None, nursing_dependency=None, 
                     care_requirements=None, patient_factors=None):
    """
    Calculate the CAMEO II score - Complexity Assessment and Monitoring to Ensure Optimal Outcomes
    
    CAMEO II is a nursing workload and acuity assessment tool for pediatric critical care.
    
    Args:
        physiologic_instability: Level of instability (0-3)
        respiratory_support: Level of respiratory support (0-3)
        oxygen_requirement: Oxygen needs (0-3)
        cardiovascular_support: Level of CV support (0-3)
        vitals_frequency: Frequency of vital sign monitoring (0-3)
        intervention_level: Level of interventions required (0-3)
        invasive_lines: Number/complexity of invasive lines (0-3)
        medication_complexity: Complexity of medication regimen (0-3)
        nursing_dependency: Level of nursing care required (0-3)
        care_requirements: Special care requirements (0-3)
        patient_factors: Additional complicating factors (0-3)
        
    Returns:
        Dictionary with total score, acuity level, and recommended staffing ratio.
        Returns 'N/A' for score and all subscores if required parameters are missing.
    """
    # Define core parameters that must be present
    critical_params = {
        'physiologic_instability': physiologic_instability,
        'respiratory_support': respiratory_support,
        'vitals_frequency': vitals_frequency,
        'nursing_dependency': nursing_dependency
    }
    
    # Define all parameters for subscore reporting
    all_params = {
        'physiologic_instability': physiologic_instability,
        'respiratory_support': respiratory_support,
        'oxygen_requirement': oxygen_requirement,
        'cardiovascular_support': cardiovascular_support,
        'vitals_frequency': vitals_frequency,
        'intervention_level': intervention_level,
        'invasive_lines': invasive_lines,
        'medication_complexity': medication_complexity,
        'nursing_dependency': nursing_dependency,
        'care_requirements': care_requirements,
        'patient_factors': patient_factors
    }
    
    # Check for missing critical parameters
    missing_params = [param for param, value in critical_params.items() if value is None]
    
    if missing_params:
        return create_na_response(
            "CAMEO II", missing_params, 
            list(all_params.keys()), 
            include_interpretation=False, include_action=True
        )
    
    # Process each parameter, using the parse_numeric_or_map function for flexibility
    subscores = {}
    
    # Define maps for string inputs
    instability_map = {
        'stable': 0, 'none': 0,
        'mild': 1, 'minimal': 1,
        'moderate': 2, 'significant': 2,
        'severe': 3, 'critical': 3
    }
    
    vitals_map = {
        'q8h': 0, 'q6h': 0, 'q4h': 0, 'standard': 0,
        'q2h': 1, 'q1h': 2,
        'continuous': 3, 'q15m': 3, 'q30m': 3
    }
    
    interventions_map = {
        'minimal': 0, 'routine': 0,
        'moderate': 1, 'intermediate': 1,
        'complex': 2, 'frequent': 2,
        'intensive': 3, 'continuous': 3
    }
    
    lines_map = {
        'none': 0, 'peripheral': 0,
        'single central': 1, 'picc': 1,
        'multiple central': 2, 'multiple picc': 2,
        'art line': 3, 'pa catheter': 3, 'multiple complex': 3
    }
    
    medication_map = {
        'none': 0, 'po only': 0, 'prn only': 0,
        'scheduled iv': 1, 'standard drips': 1,
        'multiple iv': 2, 'vasoactive drips': 2,
        'titrated drips': 3, 'multiple complex': 3
    }
    
    dependency_map = {
        'independent': 0, 'minimal': 0,
        'moderate': 1, 'extensive': 2,
        'complete': 3, 'total': 3
    }
    
    # Parse and score each parameter
    subscores['physiologic_instability'] = parse_numeric_or_map(physiologic_instability, instability_map)
    subscores['respiratory_support'] = safe_get_from_map(respiratory_support, OXYGEN_THERAPY_MAP)
    subscores['oxygen_requirement'] = parse_numeric_or_map(oxygen_requirement, OXYGEN_THERAPY_MAP) if oxygen_requirement is not None else 0
    subscores['cardiovascular_support'] = parse_numeric_or_map(cardiovascular_support, instability_map) if cardiovascular_support is not None else 0
    subscores['vitals_frequency'] = parse_numeric_or_map(vitals_frequency, vitals_map)
    subscores['intervention_level'] = parse_numeric_or_map(intervention_level, interventions_map) if intervention_level is not None else 0
    subscores['invasive_lines'] = parse_numeric_or_map(invasive_lines, lines_map) if invasive_lines is not None else 0
    subscores['medication_complexity'] = parse_numeric_or_map(medication_complexity, medication_map) if medication_complexity is not None else 0
    subscores['nursing_dependency'] = parse_numeric_or_map(nursing_dependency, dependency_map)
    subscores['care_requirements'] = parse_numeric_or_map(care_requirements, instability_map) if care_requirements is not None else 0
    subscores['patient_factors'] = parse_numeric_or_map(patient_factors, instability_map) if patient_factors is not None else 0
    
    # Calculate total score
    total_score = sum(subscores.values())
    
    # Determine acuity level and staffing ratio
    cameo_thresholds = [
        (10, "Level 1: Low Acuity", "1:3 or 1:4 nurse-to-patient ratio"),
        (20, "Level 2: Moderate Acuity", "1:2 nurse-to-patient ratio"),
        (25, "Level 3: High Acuity", "1:1 nurse-to-patient ratio"),
        (33, "Level 4: Critical Acuity", "1:1 nurse-to-patient ratio with additional support")
    ]
    
    acuity_level, staffing = normalize_to_risk_level(total_score, cameo_thresholds)
    
    return {
        "score": total_score,
        "acuity_level": acuity_level,
        "staffing_recommendation": staffing,
        "subscores": subscores
    }


def calculate_prism3(vitals=None, labs=None, age_months=None, ventilated=False):
    """
    Calculate the Pediatric Risk of Mortality III (PRISM III) score
    
    PRISM III is a physiology-based scoring system that predicts mortality risk
    in pediatric intensive care units. It evaluates 17 physiological variables
    across cardiovascular, neurological, acid-base, chemistry, and hematologic systems.
    
    Args:
        vitals: Dictionary with vital signs including:
            - 'systolic_bp': Systolic blood pressure in mmHg
            - 'diastolic_bp': Diastolic blood pressure in mmHg
            - 'heart_rate': Heart rate in bpm
            - 'temperature': Temperature in Celsius
            - 'gcs': Glasgow Coma Scale (3-15)
            - 'pupils': Pupil reactivity description
        labs: Dictionary with laboratory values including:
            - 'ph': Blood pH
            - 'pco2': PCO2 in mmHg
            - 'po2': PO2 in mmHg
            - 'bicarbonate': Bicarbonate in mEq/L
            - 'sodium': Sodium in mEq/L
            - 'potassium': Potassium in mEq/L
            - 'glucose': Glucose in mg/dL
            - 'bun': BUN in mg/dL
            - 'creatinine': Creatinine in mg/dL
            - 'wbc': White blood cell count in thousands/μL
            - 'platelets': Platelet count in thousands/μL
            - 'pt': Prothrombin time in seconds
            - 'ptt': Partial thromboplastin time in seconds
        age_months: Age in months
        ventilated: Whether patient is on mechanical ventilation
        
    Returns:
        Dictionary with total score, mortality risk, and subscores by system.
        Returns 'N/A' for score and all subscores if required parameters are missing.
    """
    # Initialize default dictionaries if None provided
    if vitals is None:
        vitals = {}
    if labs is None:
        labs = {}
    
    # Critical parameters that must be present
    if age_months is None:
        return create_na_response(
            "PRISM III", ["age_months"],
            ["cardiovascular", "neurological", "acid_base", "chemistry", "hematologic"],
            include_interpretation=True, include_action=False
        )
    
    # Initialize subscores by system
    cardiovascular_score = 0
    neurological_score = 0
    acid_base_score = 0
    chemistry_score = 0
    hematologic_score = 0
    
    # Check for minimum parameters - need at least vitals or labs
    if not vitals and not labs:
        return create_na_response(
            "PRISM III", ["vitals", "labs"],
            ["cardiovascular", "neurological", "acid_base", "chemistry", "hematologic"],
            include_interpretation=True, include_action=False
        )
    
    # Get age-appropriate vital sign ranges
    ranges = get_age_based_ranges(age_months)
    age_years = age_months / 12
    
    # Cardiovascular scoring
    sbp = vitals.get('systolic_bp')
    heart_rate = vitals.get('heart_rate')
    
    # SBP thresholds vary by age
    if sbp is not None:
        if age_months < 12:  # <1 year
            if sbp < 40:
                cardiovascular_score += 7
            elif sbp < 55:
                cardiovascular_score += 3
        elif age_months < 60:  # 1-4 years
            if sbp < 45:
                cardiovascular_score += 7
            elif sbp < 65:
                cardiovascular_score += 3
        elif age_months < 144:  # 5-11 years
            if sbp < 55:
                cardiovascular_score += 7
            elif sbp < 75:
                cardiovascular_score += 3
        else:  # ≥12 years
            if sbp < 65:
                cardiovascular_score += 7
            elif sbp < 85:
                cardiovascular_score += 3
    
    # Heart rate scoring
    if heart_rate is not None:
        hr_min, hr_max = ranges['heart_rate']
        if heart_rate < hr_min - 30 or heart_rate > hr_max + 40:
            cardiovascular_score += 4
        elif heart_rate < hr_min - 10 or heart_rate > hr_max + 20:
            cardiovascular_score += 3
    
    # Temperature scoring
    if 'temperature' in vitals and vitals['temperature'] is not None:
        if vitals['temperature'] < 33.0:
            cardiovascular_score += 3
    
    # Neurological scoring
    if 'gcs' in vitals and vitals['gcs'] is not None:
        try:
            gcs = int(vitals['gcs'])
            if gcs < 8:
                neurological_score += 5
            elif gcs < 12:
                neurological_score += 2
        except (ValueError, TypeError):
            pass  # Skip GCS if not a valid number
    
    # Pupil reactivity
    if 'pupils' in vitals and vitals['pupils'] is not None:
        pupils = str(vitals['pupils']).lower()
        if 'fixed' in pupils or 'nonreactive' in pupils or 'dilated' in pupils:
            neurological_score += 7
    
    # Acid-base and blood gas scoring
    if 'ph' in labs and labs['ph'] is not None:
        ph = labs['ph']
        if ph < 7.0:
            acid_base_score += 6
        elif ph < 7.28:
            acid_base_score += 3
        elif ph > 7.55:
            acid_base_score += 3
    
    if 'pco2' in labs and labs['pco2'] is not None:
        pco2 = labs['pco2']
        if pco2 > 75:
            acid_base_score += 3
    
    if 'bicarbonate' in labs and labs['bicarbonate'] is not None:
        bicarb = labs['bicarbonate']
        if bicarb < 16:
            acid_base_score += 3
        elif bicarb > 32:
            acid_base_score += 3
    
    # For PO2/FiO2 ratio, need ventilation status
    if ventilated and 'po2' in labs and labs['po2'] is not None:
        po2 = labs['po2']
        # Assuming FiO2 is around 0.4 for a rough calculation
        fio2 = 0.4  # This should ideally be provided as a parameter
        pf_ratio = po2 / fio2
        if pf_ratio < 200:
            acid_base_score += 3
    
    # Chemistry scoring
    if 'glucose' in labs and labs['glucose'] is not None:
        glucose = labs['glucose']
        if glucose > 200:
            chemistry_score += 2
        elif glucose < 50:
            chemistry_score += 2
    
    if 'potassium' in labs and labs['potassium'] is not None:
        potassium = labs['potassium']
        if potassium > 6.5:
            chemistry_score += 3
    
    if 'creatinine' in labs and labs['creatinine'] is not None:
        creatinine = labs['creatinine']
        # Creatinine thresholds vary by age
        if age_months < 12 and creatinine > 0.85:
            chemistry_score += 2
        elif age_months < 60 and creatinine > 0.9:
            chemistry_score += 2
        elif age_months < 144 and creatinine > 1.3:
            chemistry_score += 2
        elif creatinine > 1.5:
            chemistry_score += 2
    
    if 'bun' in labs and labs['bun'] is not None:
        bun = labs['bun']
        if bun > 36:
            chemistry_score += 3
    
    # Hematologic scoring
    if 'wbc' in labs and labs['wbc'] is not None:
        wbc = labs['wbc']
        if wbc < 3.0:
            hematologic_score += 4
    
    if 'platelets' in labs and labs['platelets'] is not None:
        platelets = labs['platelets']
        if platelets < 50:
            hematologic_score += 2
        elif platelets < 100:
            hematologic_score += 1
    
    if 'pt' in labs and labs['pt'] is not None and 'ptt' in labs and labs['ptt'] is not None:
        pt = labs['pt']
        ptt = labs['ptt']
        # PT/PTT thresholds
        if pt > 22 or ptt > 57:
            hematologic_score += 3
    
    # Calculate total score
    total_score = (
        cardiovascular_score + neurological_score + acid_base_score +
        chemistry_score + hematologic_score
    )
    
    # Interpret total score for mortality risk
    # These are approximate mortality rates based on PRISM III score ranges
    if total_score < 10:
        mortality_risk = "Low risk: <5% mortality"
    elif total_score < 20:
        mortality_risk = "Moderate risk: 5-15% mortality"
    elif total_score < 30:
        mortality_risk = "High risk: 15-30% mortality"
    else:  # score >= 30
        mortality_risk = "Very high risk: >30% mortality"
    
    return {
        "score": total_score,
        "interpretation": mortality_risk,
        "subscores": {
            "cardiovascular": cardiovascular_score,
            "neurological": neurological_score,
            "acid_base": acid_base_score,
            "chemistry": chemistry_score,
            "hematologic": hematologic_score
        }
    }


def calculate_queensland_non_trauma(resp_rate=None, HR=None, mental_status=None, SpO2=None, age_months=None):
    """
    Calculate the Queensland Pediatric Non-Trauma Early Warning Score
    
    This system is used for early identification of pediatric patients at risk of deterioration
    in non-trauma settings, commonly used in Australia.
    
    Args:
        resp_rate: Respiratory rate in breaths per minute
        HR: Heart rate in beats per minute
        mental_status: Mental status descriptor ('alert', 'voice', 'pain', 'unresponsive')
        SpO2: Oxygen saturation percentage
        age_months: Age in months (for age-appropriate vital sign thresholds)
        
    Returns:
        Dictionary with score, risk level, action recommendations, and age category.
        Returns 'N/A' for score and all metrics if required parameters are missing.
    """
    # Check for required parameters
    required_params = {
        'resp_rate': resp_rate,
        'HR': HR,
        'mental_status': mental_status
    }
    
    # Critical parameters for score calculation
    critical_params = {
        'resp_rate': resp_rate,
        'HR': HR
    }
    
    # Check for missing critical parameters
    missing_critical = [param for param, value in critical_params.items() if value is None]
    if missing_critical or age_months is None:
        return create_na_response(
            "Queensland Non-Trauma", 
            missing_critical + ([] if age_months is not None else ["age_months"]),
            ["respiratory_rate", "heart_rate", "mental_status", "spo2"],
            include_interpretation=False
        )
    
    # Determine age category
    if age_months < 12:  # <1 year
        age_category = "Infant (<1 year)"
    elif age_months < 60:  # 1-4 years
        age_category = "Toddler (1-4 years)"
    elif age_months < 144:  # 5-11 years
        age_category = "School Age (5-11 years)"
    else:  # 12+ years
        age_category = "Adolescent (12+ years)"
    
    # Initialize subscores
    subscores = {}
    
    # Score respiratory rate based on age category
    if age_months < 12:  # Infant <1 year
        if resp_rate < 20:
            subscores["respiratory_rate"] = 3
        elif resp_rate < 25:
            subscores["respiratory_rate"] = 2
        elif resp_rate < 30:
            subscores["respiratory_rate"] = 1
        elif resp_rate > 60:
            subscores["respiratory_rate"] = 3
        elif resp_rate > 50:
            subscores["respiratory_rate"] = 2
        elif resp_rate > 40:
            subscores["respiratory_rate"] = 1
        else:
            subscores["respiratory_rate"] = 0
    elif age_months < 60:  # Toddler 1-4 years
        if resp_rate < 15:
            subscores["respiratory_rate"] = 3
        elif resp_rate < 20:
            subscores["respiratory_rate"] = 2
        elif resp_rate < 25:
            subscores["respiratory_rate"] = 1
        elif resp_rate > 40:
            subscores["respiratory_rate"] = 3
        elif resp_rate > 35:
            subscores["respiratory_rate"] = 2
        elif resp_rate > 30:
            subscores["respiratory_rate"] = 1
        else:
            subscores["respiratory_rate"] = 0
    elif age_months < 144:  # School Age 5-11 years
        if resp_rate < 10:
            subscores["respiratory_rate"] = 3
        elif resp_rate < 15:
            subscores["respiratory_rate"] = 2
        elif resp_rate < 20:
            subscores["respiratory_rate"] = 1
        elif resp_rate > 35:
            subscores["respiratory_rate"] = 3
        elif resp_rate > 30:
            subscores["respiratory_rate"] = 2
        elif resp_rate > 25:
            subscores["respiratory_rate"] = 1
        else:
            subscores["respiratory_rate"] = 0
    else:  # Adolescent 12+ years
        if resp_rate < 10:
            subscores["respiratory_rate"] = 3
        elif resp_rate < 12:
            subscores["respiratory_rate"] = 2
        elif resp_rate < 15:
            subscores["respiratory_rate"] = 1
        elif resp_rate > 30:
            subscores["respiratory_rate"] = 3
        elif resp_rate > 25:
            subscores["respiratory_rate"] = 2
        elif resp_rate > 20:
            subscores["respiratory_rate"] = 1
        else:
            subscores["respiratory_rate"] = 0
    
    # Score heart rate based on age category
    if age_months < 12:  # Infant <1 year
        if HR < 90:
            subscores["heart_rate"] = 3
        elif HR < 110:
            subscores["heart_rate"] = 2
        elif HR < 120:
            subscores["heart_rate"] = 1
        elif HR > 170:
            subscores["heart_rate"] = 3
        elif HR > 150:
            subscores["heart_rate"] = 2
        elif HR > 140:
            subscores["heart_rate"] = 1
        else:
            subscores["heart_rate"] = 0
    elif age_months < 60:  # Toddler 1-4 years
        if HR < 80:
            subscores["heart_rate"] = 3
        elif HR < 95:
            subscores["heart_rate"] = 2
        elif HR < 110:
            subscores["heart_rate"] = 1
        elif HR > 160:
            subscores["heart_rate"] = 3
        elif HR > 140:
            subscores["heart_rate"] = 2
        elif HR > 130:
            subscores["heart_rate"] = 1
        else:
            subscores["heart_rate"] = 0
    elif age_months < 144:  # School Age 5-11 years
        if HR < 70:
            subscores["heart_rate"] = 3
        elif HR < 80:
            subscores["heart_rate"] = 2
        elif HR < 90:
            subscores["heart_rate"] = 1
        elif HR > 140:
            subscores["heart_rate"] = 3
        elif HR > 130:
            subscores["heart_rate"] = 2
        elif HR > 120:
            subscores["heart_rate"] = 1
        else:
            subscores["heart_rate"] = 0
    else:  # Adolescent 12+ years
        if HR < 60:
            subscores["heart_rate"] = 3
        elif HR < 65:
            subscores["heart_rate"] = 2
        elif HR < 70:
            subscores["heart_rate"] = 1
        elif HR > 130:
            subscores["heart_rate"] = 3
        elif HR > 120:
            subscores["heart_rate"] = 2
        elif HR > 110:
            subscores["heart_rate"] = 1
        else:
            subscores["heart_rate"] = 0
    
    # Score mental status
    subscores["mental_status"] = safe_get_from_map(mental_status, MENTAL_STATUS_MAP)
    
    # Score SpO2
    if SpO2 is not None:
        if SpO2 < 85:
            subscores["spo2"] = 3
        elif SpO2 < 90:
            subscores["spo2"] = 2
        elif SpO2 < 94:
            subscores["spo2"] = 1
        else:
            subscores["spo2"] = 0
    else:
        subscores["spo2"] = 0  # Default if not provided
    
    # Calculate total score
    total_score = sum(subscores.values())
    
    # Determine risk level and action
    qld_thresholds = [
        (3, "Low Risk", "Routine observation and care"),
        (5, "Medium Risk", "Increase observation frequency; consider medical review"),
        (7, "High Risk", "Urgent medical review required; consider PICU notification"),
        (12, "Critical Risk", "Immediate medical and senior nursing review; PICU notification")
    ]
    
    risk_level, action = normalize_to_risk_level(total_score, qld_thresholds)
    
    return {
        "score": total_score,
        "risk_level": risk_level,
        "action": action,
        "age_category": age_category,
        "subscores": subscores
    }


def calculate_queensland_trauma(mechanism=None, consciousness=None, airway=None, breathing=None, circulation=None):
    """
    Calculate the Queensland Pediatric Trauma Score
    
    This scoring system is used for rapid assessment of trauma severity in pediatric patients,
    commonly used in Australian emergency settings.
    
    Args:
        mechanism: Description of trauma mechanism ('minor', 'moderate', 'severe', 'critical')
        consciousness: Description of level of consciousness ('alert', 'voice', 'pain', 'unresponsive')
        airway: Description of airway status ('clear', 'maintainable', 'unmaintainable')
        breathing: Description of breathing status ('normal', 'distressed', 'absent/inadequate')
        circulation: Description of circulatory status ('normal', 'abnormal', 'decompensated')
        
    Returns:
        Dictionary with score, risk level, and action recommendations.
        Returns 'N/A' if critical parameters are missing.
    """
    # All parameters are required for this score
    required_params = {
        'mechanism': mechanism,
        'consciousness': consciousness,
        'airway': airway,
        'breathing': breathing,
        'circulation': circulation
    }
    
    missing_params = [param for param, value in required_params.items() if value is None]
    if missing_params:
        return create_na_response(
            "Queensland Trauma", missing_params,
            list(required_params.keys()),
            include_interpretation=False
        )
    
    # Initialize subscores
    subscores = {}
    
    # Score mechanism of injury
    mechanism_map = {
        'minor': 0, 'low energy': 0, 'isolated': 0,
        'moderate': 1, 'medium energy': 1,
        'severe': 2, 'high energy': 2, 'multiple': 2, 'high-energy': 2,
        'critical': 3, 'very high energy': 3, 'extreme': 3
    }
    subscores['mechanism'] = safe_get_from_map(mechanism, mechanism_map)
    
    # Score consciousness
    subscores['consciousness'] = safe_get_from_map(consciousness, MENTAL_STATUS_MAP)
    
    # Score airway
    airway_map = {
        'clear': 0, 'patent': 0, 'normal': 0,
        'maintainable': 1, 'requires support': 1, 'assisted': 1,
        'unmaintainable': 2, 'compromised': 2, 'intervention required': 2,
        'obstructed': 3, 'failed': 3, 'intubated': 3
    }
    subscores['airway'] = safe_get_from_map(airway, airway_map)
    
    # Score breathing
    breathing_map = {
        'normal': 0, 'comfortable': 0, 'regular': 0, 'unlabored': 0,
        'distressed': 1, 'increased work': 1, 'mild increased work': 1, 'moderate work': 1,
        'labored': 2, 'severe distress': 2, 'significant work': 2, 'retractions': 2,
        'absent': 3, 'inadequate': 3, 'apneic': 3, 'failing': 3
    }
    subscores['breathing'] = safe_get_from_map(breathing, breathing_map)
    
    # Score circulation
    circulation_map = {
        'normal': 0, 'good': 0, 'stable': 0,
        'abnormal': 1, 'mild tachycardia': 1, 'delayed capillary refill': 1,
        'unstable': 2, 'tachycardic': 2, 'poor perfusion': 2,
        'decompensated': 3, 'shock': 3, 'absent pulses': 3, 'failure': 3
    }
    subscores['circulation'] = safe_get_from_map(circulation, circulation_map)
    
    # Calculate total score
    total_score = sum(subscores.values())
    
    # Determine risk level and action
    trauma_thresholds = [
        (3, "Low Risk", "Consider ED assessment; may not require trauma team"),
        (6, "Medium Risk", "Trauma team assessment required; may not need immediate resuscitation"),
        (9, "High Risk", "Immediate trauma team activation; resuscitation likely required"),
        (15, "Critical Risk", "Highest level trauma activation; immediate life-saving interventions")
    ]
    
    risk_level, action = normalize_to_risk_level(total_score, trauma_thresholds)
    
    return {
        "score": total_score,
        "risk_level": risk_level,
        "action": action,
        "subscores": subscores
    }


def calculate_tps(respiratory_status=None, circulation_status=None, neurologic_status=None):
    """
    Calculate the Transport Physiology Score (TPS)
    
    This score is used to assess physiological derangement during pediatric transport.
    It's designed to be quick to calculate with minimal parameters.
    
    Args:
        respiratory_status: Description of respiratory status (0-3 or text description)
        circulation_status: Description of circulation status (0-3 or text description)
        neurologic_status: Description of neurologic status (0-3 or text description)
        
    Returns:
        Dictionary with score, risk level, and transport recommendations.
        Returns 'N/A' if all parameters are missing.
    """
    # Check if all parameters are missing
    if respiratory_status is None and circulation_status is None and neurologic_status is None:
        return create_na_response(
            "TPS", 
            ["respiratory_status", "circulation_status", "neurologic_status"],
            ["respiratory", "circulation", "neurologic"],
            include_interpretation=False
        )
    
    # Define maps for string inputs
    respiratory_map = {
        'normal': 0, 'stable': 0, 'no distress': 0,
        'mild': 1, 'minor': 1, 'slight': 1, 'minimal distress': 1,
        'moderate': 2, 'significant': 2, 'distressed': 2, 'moderate distress': 2,
        'severe': 3, 'critical': 3, 'intubated': 3, 'respiratory failure': 3, 'severe distress': 3
    }
    
    circulation_map = {
        'normal': 0, 'stable': 0, 'good perfusion': 0,
        'mild': 1, 'minor': 1, 'compensated': 1, 'mild tachycardia': 1, 
        'moderate': 2, 'significant': 2, 'compromised': 2, 'poor perfusion': 2,
        'severe': 3, 'critical': 3, 'shock': 3, 'decompensated': 3, 'failure': 3
    }
    
    # Initialize subscores
    subscores = {
        "respiratory": parse_numeric_or_map(respiratory_status, respiratory_map) if respiratory_status is not None else 0,
        "circulation": parse_numeric_or_map(circulation_status, circulation_map) if circulation_status is not None else 0,
        "neurologic": parse_numeric_or_map(neurologic_status, MENTAL_STATUS_MAP) if neurologic_status is not None else 0
    }
    
    # Calculate total score - max is 9 (3 in each category)
    total_score = sum(subscores.values())
    
    # Determine risk level and transport team recommendation
    tps_thresholds = [
        (2, "Low Risk", "Standard transport team"),
        (4, "Moderate Risk", "Advanced care provider recommended"),
        (6, "High Risk", "Critical care transport team required"),
        (9, "Critical Risk", "Critical care transport team with physician required")
    ]
    
    risk_level, transport_recommendation = normalize_to_risk_level(total_score, tps_thresholds)
    
    return {
        "score": total_score,
        "risk_level": risk_level,
        "transport_recommendation": transport_recommendation,
        "subscores": subscores
    }


def calculate_chews(respiratory_rate=None, respiratory_effort=None, heart_rate=None, systolic_bp=None, 
                   capillary_refill=None, oxygen_therapy=None, oxygen_saturation=None, age_months=None):
    """
    Calculate the Children's Hospital Early Warning Score (CHEWS)
    
    This score is designed to identify clinical deterioration in hospitalized children.
    It includes multiple physiological parameters and is age-adjusted.
    
    Args:
        respiratory_rate: Breaths per minute
        respiratory_effort: Description of respiratory effort ('normal', 'increased', etc.)
        heart_rate: Beats per minute
        systolic_bp: Systolic blood pressure in mmHg
        capillary_refill: Time in seconds
        oxygen_therapy: Type of oxygen support ('none', 'nasal cannula', etc.)
        oxygen_saturation: SpO2 percentage
        age_months: Age in months (for age-appropriate thresholds)
        
    Returns:
        Dictionary with score, alert level, action recommendations, and subscores.
        Returns 'N/A' for score and all metrics if required parameters are missing.
    """
    # Check for minimum required parameters
    critical_params = {
        'respiratory_rate': respiratory_rate,
        'heart_rate': heart_rate,
        'age_months': age_months
    }
    
    # Define subscore keys for consistent NA responses
    subscore_keys = [
        "respiratory_rate", "respiratory_effort", "heart_rate", 
        "systolic_bp", "capillary_refill", "oxygen_therapy", "oxygen_saturation"
    ]
    
    # Check for missing critical parameters
    missing_critical = [param for param, value in critical_params.items() if value is None]
    if missing_critical:
        response = create_na_response("CHEWS", missing_critical, subscore_keys)
        response["alert_level"] = "Cannot calculate: missing critical parameters"
        response["normal_ranges"] = {}
        return response
    
    # Get reference ranges for this age
    ranges = get_age_based_ranges(age_months)
    hr_min, hr_max = ranges['heart_rate']
    rr_min, rr_max = ranges['respiratory_rate']
    
    # Approximation of normal systolic BP by age
    # Rule of thumb: 70 + (2 × age in years)
    normal_sbp = 70 + (2 * (age_months / 12))
    
    # Initialize subscores
    subscores = {}
    
    # Score respiratory rate
    resp_rate_score = 0
    if respiratory_rate < rr_min - 10:
        resp_rate_score = 3
    elif respiratory_rate < rr_min - 5:
        resp_rate_score = 2
    elif respiratory_rate < rr_min:
        resp_rate_score = 1
    elif respiratory_rate > rr_max + 15:
        resp_rate_score = 3
    elif respiratory_rate > rr_max + 10:
        resp_rate_score = 2
    elif respiratory_rate > rr_max + 5:
        resp_rate_score = 1
    
    subscores["respiratory_rate"] = resp_rate_score
    
    # Score respiratory effort
    subscores["respiratory_effort"] = safe_get_from_map(respiratory_effort, RESPIRATORY_EFFORT_MAP)
    
    # Score heart rate
    hr_score = 0
    if heart_rate < hr_min - 20:
        hr_score = 3
    elif heart_rate < hr_min - 10:
        hr_score = 2
    elif heart_rate < hr_min:
        hr_score = 1
    elif heart_rate > hr_max + 20:
        hr_score = 3
    elif heart_rate > hr_max + 15:
        hr_score = 2
    elif heart_rate > hr_max + 10:
        hr_score = 1
    
    subscores["heart_rate"] = hr_score
    
    # Score systolic blood pressure
    sbp_score = 0
    if systolic_bp is not None:
        if systolic_bp < normal_sbp - 20:
            sbp_score = 3
        elif systolic_bp < normal_sbp - 10:
            sbp_score = 2
        elif systolic_bp < normal_sbp - 5:
            sbp_score = 1
    
    subscores["systolic_bp"] = sbp_score
    
    # Score capillary refill
    cap_refill_score = 0
    if capillary_refill is not None:
        if capillary_refill > 4:
            cap_refill_score = 3
        elif capillary_refill > 3:
            cap_refill_score = 2
        elif capillary_refill > 2:
            cap_refill_score = 1
    
    subscores["capillary_refill"] = cap_refill_score
    
    # Score oxygen therapy
    subscores["oxygen_therapy"] = safe_get_from_map(oxygen_therapy, OXYGEN_THERAPY_MAP)
    
    # Score oxygen saturation
    o2_sat_score = 0
    if oxygen_saturation is not None:
        if oxygen_saturation < 85:
            o2_sat_score = 3
        elif oxygen_saturation < 90:
            o2_sat_score = 2
        elif oxygen_saturation < 93:
            o2_sat_score = 1
    
    subscores["oxygen_saturation"] = o2_sat_score
    
    # Calculate total score
    total_score = sum(subscores.values())
    
    # Define alert level thresholds
    chews_thresholds = [
        (2, "Low Alert Level", "Routine care; reassess per unit standard"),
        (4, "Medium Alert Level", "Increase assessment frequency; consider medical review"),
        (6, "High Alert Level", "Urgent medical review required; consider PICU consult"),
        (999, "Critical Alert Level", "Immediate medical intervention; PICU consult/transfer indicated")
    ]
    
    alert_level, action = normalize_to_risk_level(total_score, chews_thresholds)
    
    return {
        "score": total_score,
        "alert_level": alert_level,
        "action": action,
        "subscores": subscores,
        "normal_ranges": {
            "heart_rate": f"{hr_min}-{hr_max} bpm",
            "respiratory_rate": f"{rr_min}-{rr_max} bpm",
            "systolic_bp": f"~{int(normal_sbp)} mmHg"
        }
    }
