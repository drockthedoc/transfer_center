# Pediatric Illness Severity Scoring Functions

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
from typing import Any, Dict, List, Optional, Tuple, Union

# Import utility functions and constants
from docs.pediatric_scoring_utils import (
    BEHAVIOR_MAP,
    HEMODYNAMIC_MAP,
    MENTAL_STATUS_MAP,
    OXYGEN_THERAPY_MAP,
    RESPIRATORY_EFFORT_MAP,
    check_missing_params,
    create_na_response,
    get_age_based_ranges,
    normalize_to_risk_level,
    safe_get_from_map,
)

logger = logging.getLogger(__name__)

# PEWS - Pediatric Early Warning Score


def calculate_pews(
    age_months=None,
    respiratory_rate=None,
    respiratory_effort=None,
    oxygen_requirement=None,
    heart_rate=None,
    capillary_refill=None,
    behavior=None,
):
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
        "respiratory_rate": respiratory_rate,
        "respiratory_effort": respiratory_effort,
        "heart_rate": heart_rate,
        "behavior": behavior,
    }

    missing_params = [
        param for param, value in required_params.items() if value is None
    ]
    if missing_params:
        return create_na_response(
            "PEWS",
            missing_params,
            ["respiratory", "cardiovascular", "behavior"],
            include_interpretation=True,
            include_action=True,
        )

    # Check if age is missing
    if age_months is None:
        return create_na_response(
            "PEWS",
            ["age_months"],
            ["respiratory", "cardiovascular", "behavior"],
            include_interpretation=True,
            include_action=True,
        )

    # Get reference ranges for this age
    ranges = get_age_based_ranges(age_months)

    # Initialize subscores
    respiratory_subscore = 0
    cardiovascular_subscore = 0
    behavior_subscore = 0

    # Score respiratory parameters
    rr_min, rr_max = ranges["respiratory_rate"]

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
    respiratory_subscore += safe_get_from_map(
        respiratory_effort, RESPIRATORY_EFFORT_MAP
    )

    # Oxygen requirement scoring
    oxygen_score = safe_get_from_map(oxygen_requirement, OXYGEN_THERAPY_MAP)
    respiratory_subscore = max(respiratory_subscore, oxygen_score)

    # Score cardiovascular parameters
    hr_min, hr_max = ranges["heart_rate"]

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
        if capillary_refill >= 5:
            cardiovascular_subscore = max(cardiovascular_subscore, 3)
        elif capillary_refill >= 3:
            cardiovascular_subscore = max(cardiovascular_subscore, 2)
        elif capillary_refill >= 2:
            cardiovascular_subscore = max(cardiovascular_subscore, 1)

    # Score behavior
    behavior_subscore = safe_get_from_map(behavior, BEHAVIOR_MAP)

    # Calculate total score
    total_score = respiratory_subscore + cardiovascular_subscore + behavior_subscore

    # Define thresholds for interpretation
    pews_thresholds = [
        (2, "Routine monitoring", "Continue routine care"),
        (
            4,
            "Increased monitoring needed",
            "Increase frequency of observations; consider notifying medical team",
        ),
        (
            6,
            "Medical review needed",
            "Request urgent medical review; consider PICU consult",
        ),
        (
            999,
            "Critical situation",
            "Immediate medical intervention; PICU consult/transfer indicated",
        ),
    ]

    interpretation, action = normalize_to_risk_level(total_score, pews_thresholds)

    # Check for critical parameters
    has_critical = (
        respiratory_subscore >= 3
        or cardiovascular_subscore >= 3
        or behavior_subscore >= 3
    )

    return {
        "score": total_score,
        "interpretation": interpretation,
        "action": action,
        "subscores": {
            "respiratory": respiratory_subscore,
            "cardiovascular": cardiovascular_subscore,
            "behavior": behavior_subscore,
        },
        "critical_parameter": has_critical,
    }


def calculate_trap(
    respiratory_support=None,
    respiratory_rate=None,
    work_of_breathing=None,
    oxygen_saturation=None,
    hemodynamic_stability=None,
    blood_pressure=None,
    heart_rate=None,
    neuro_status=None,
    gcs=None,
    access_difficulty=None,
    age_months=None,
):
    """
    Calculate the Transport Risk Assessment in Pediatrics (TRAP) Score

    The TRAP score helps assess the risk of deterioration during inter-facility transport.
    It evaluates respiratory, hemodynamic, neurologic, and access domains.

    Args:
        respiratory_support: Type of support ('room air', 'nasal cannula', 'high-flow', 'cpap/bipap', 'ventilator')
        respiratory_rate: Breaths per minute (optional, enhances respiratory subscore)
        work_of_breathing: Descriptor ('none', 'mild', 'moderate', 'severe') (optional)
        oxygen_saturation: SpO2 percentage (optional)
        hemodynamic_stability: Descriptor ('stable', 'compensated', 'decompensated')
        blood_pressure: Systolic BP (optional, enhances hemodynamic subscore)
        heart_rate: Beats per minute (optional, enhances hemodynamic subscore)
        neuro_status: Neurological status ('normal', 'altered', 'severely altered')
        gcs: Glasgow Coma Scale (optional, enhances neuro subscore)
        access_difficulty: Difficulty obtaining vascular access ('yes'/'no')
        age_months: Age in months (optional, used for reference ranges)

    Returns:
        Dictionary with total score, risk level, and subscores. Returns 'N/A' for score and subscores
        if required parameters are missing.
    """
    # Check for required parameters
    required_params = {
        "respiratory_support": respiratory_support,
        "hemodynamic_stability": hemodynamic_stability,
        "neuro_status": neuro_status,
        "access_difficulty": access_difficulty,
    }

    missing_params = [
        param for param, value in required_params.items() if value is None
    ]
    if missing_params:
        response = create_na_response(
            "TRAP",
            missing_params,
            ["respiratory", "hemodynamic", "neurologic", "access"],
            include_interpretation=False,
            include_action=False,
        )
        response["risk_level"] = "Cannot calculate: missing required parameters"
        response["team_recommendation"] = "N/A"
        return response

    # Initialize subscores
    respiratory_subscore = 0
    hemodynamic_subscore = 0
    neuro_subscore = 0
    access_subscore = 0

    # Score respiratory support
    resp_support_map = {
        "room air": 0,
        "none": 0,
        "ra": 0,
        "nasal cannula": 1,
        "nc": 1,
        "low flow": 1,
        "simple mask": 1,
        "high flow": 2,
        "hfnc": 2,
        "non-rebreather": 2,
        "cpap": 2,
        "bipap": 2,
        "niv": 2,
        "ventilator": 3,
        "intubated": 3,
        "mechanical ventilation": 3,
        "et tube": 3,
    }

    respiratory_subscore = safe_get_from_map(respiratory_support, resp_support_map)

    # Additional respiratory assessment if vitals available
    if work_of_breathing is not None:
        work_score = safe_get_from_map(work_of_breathing, RESPIRATORY_EFFORT_MAP)
        respiratory_subscore = max(respiratory_subscore, work_score)

    if oxygen_saturation is not None:
        try:
            spo2 = float(oxygen_saturation)
            if spo2 < 85:
                respiratory_subscore = max(respiratory_subscore, 3)
            elif spo2 < 90:
                respiratory_subscore = max(respiratory_subscore, 2)
            elif spo2 < 94:
                respiratory_subscore = max(respiratory_subscore, 1)
        except (ValueError, TypeError):
            logger.warning(f"Invalid oxygen saturation value: {oxygen_saturation}")

    if respiratory_rate is not None and age_months is not None:
        try:
            rr = float(respiratory_rate)
            ranges = get_age_based_ranges(age_months)
            rr_min, rr_max = ranges["respiratory_rate"]

            if rr < rr_min - 10 or rr > rr_max + 15:
                respiratory_subscore = max(respiratory_subscore, 2)
            elif rr < rr_min - 5 or rr > rr_max + 10:
                respiratory_subscore = max(respiratory_subscore, 1)
        except (ValueError, TypeError):
            logger.warning(f"Invalid respiratory rate value: {respiratory_rate}")

    # Score hemodynamic parameters
    hemodynamic_subscore = safe_get_from_map(hemodynamic_stability, HEMODYNAMIC_MAP)

    # Additional hemodynamic assessment if available
    if blood_pressure is not None and age_months is not None:
        try:
            # Approximate normal systolic BP by age
            age_years = age_months / 12
            normal_sbp = 70 + (2 * age_years)  # Simplified formula

            sbp = float(blood_pressure)
            if sbp < normal_sbp - 20:
                hemodynamic_subscore = max(hemodynamic_subscore, 2)
            elif sbp < normal_sbp - 10:
                hemodynamic_subscore = max(hemodynamic_subscore, 1)
        except (ValueError, TypeError):
            logger.warning(f"Invalid blood pressure value: {blood_pressure}")

    if heart_rate is not None and age_months is not None:
        try:
            hr = float(heart_rate)
            ranges = get_age_based_ranges(age_months)
            hr_min, hr_max = ranges["heart_rate"]

            if hr < hr_min - 20 or hr > hr_max + 30:
                hemodynamic_subscore = max(hemodynamic_subscore, 2)
            elif hr < hr_min - 10 or hr > hr_max + 20:
                hemodynamic_subscore = max(hemodynamic_subscore, 1)
        except (ValueError, TypeError):
            logger.warning(f"Invalid heart rate value: {heart_rate}")

    # Score neurological parameters
    neuro_map = {
        "normal": 0,
        "alert": 0,
        "appropriate": 0,
        "altered": 1,
        "irritable": 1,
        "lethargic": 1,
        "confused": 1,
        "severely altered": 2,
        "obtunded": 2,
        "unresponsive": 2,
        "coma": 2,
        "seizure": 2,
    }

    neuro_subscore = safe_get_from_map(neuro_status, neuro_map)

    # Additional neurological assessment if GCS available
    if gcs is not None:
        try:
            gcs_value = int(gcs)
            if gcs_value <= 8:
                neuro_subscore = max(neuro_subscore, 2)
            elif gcs_value <= 12:
                neuro_subscore = max(neuro_subscore, 1)
        except (ValueError, TypeError):
            logger.warning(f"Invalid GCS value: {gcs}")

    # Score access difficulty
    access_map = {
        "no": 0,
        "none": 0,
        "easy": 0,
        "yes": 1,
        "difficult": 1,
        "challenging": 1,
        "multiple attempts": 2,
        "unsuccessful": 2,
        "failed": 2,
    }

    access_subscore = safe_get_from_map(access_difficulty, access_map)

    # Calculate total score
    total_score = (
        respiratory_subscore + hemodynamic_subscore + neuro_subscore + access_subscore
    )

    # Define risk thresholds
    trap_thresholds = [
        (3, "Low Risk", "Standard transport team; routine monitoring"),
        (6, "Moderate Risk", "Enhanced monitoring; consider advanced transport team"),
        (
            999,
            "High Risk",
            "Critical care transport team required; continuous monitoring",
        ),
    ]

    risk_level, team_recommendation = normalize_to_risk_level(
        total_score, trap_thresholds
    )

    return {
        "score": total_score,
        "risk_level": risk_level,
        "team_recommendation": team_recommendation,
        "subscores": {
            "respiratory": respiratory_subscore,
            "hemodynamic": hemodynamic_subscore,
            "neurologic": neuro_subscore,
            "access": access_subscore,
        },
    }


def calculate_cameo2(
    physiologic_instability=None,
    respiratory_support=None,
    oxygen_requirement=None,
    cardiovascular_support=None,
    vitals_frequency=None,
    intervention_level=None,
    invasive_lines=None,
    medication_complexity=None,
    nursing_dependency=None,
    care_requirements=None,
    patient_factors=None,
):
    """
    Calculate the CAMEO II score - Complexity Assessment and Monitoring to Ensure Optimal Outcomes

    CAMEO II is a nursing workload and acuity assessment tool for pediatric critical care.

    Args:
        physiologic_instability: Level of instability (0-3)
        respiratory_support: Level of support (0-3)
        oxygen_requirement: O2 needs (0-3)
        cardiovascular_support: Level of support (0-3)
        vitals_frequency: How often vitals are checked (0-3)
        intervention_level: Frequency/complexity of interventions (0-3)
        invasive_lines: Number and complexity of lines (0-3)
        medication_complexity: Complexity of medication regimen (0-3)
        nursing_dependency: Level of nursing care needed (0-3)
        care_requirements: Special care needs (0-3)
        patient_factors: Additional complexity factors (0-3)

    Returns:
        Dictionary with score, acuity level, and nursing recommendation. Returns 'N/A' if required
        parameters are missing.
    """
    # List of all parameters
    all_params = {
        "physiologic_instability": physiologic_instability,
        "respiratory_support": respiratory_support,
        "oxygen_requirement": oxygen_requirement,
        "cardiovascular_support": cardiovascular_support,
        "vitals_frequency": vitals_frequency,
        "intervention_level": intervention_level,
        "invasive_lines": invasive_lines,
        "medication_complexity": medication_complexity,
        "nursing_dependency": nursing_dependency,
        "care_requirements": care_requirements,
        "patient_factors": patient_factors,
    }

    # Count how many are missing
    missing_params = [param for param, value in all_params.items() if value is None]

    # If more than 2 params are missing, we can't calculate accurately
    if len(missing_params) > 2:
        response = create_na_response("CAMEO II", missing_params, [])
        response["acuity_level"] = "Cannot calculate: too many missing parameters"
        response["nursing_recommendation"] = "N/A"
        return response

    # Map string values to numeric if needed
    param_scores = {}

    # Physiologic instability mapping
    instability_map = {
        "none": 0,
        "stable": 0,
        "minimal": 0,
        "mild": 1,
        "occasional": 1,
        "moderate": 2,
        "frequent": 2,
        "severe": 3,
        "constant": 3,
        "unstable": 3,
    }
    param_scores["physiologic_instability"] = parse_numeric_or_map(
        physiologic_instability, instability_map, default=0
    )

    # Respiratory support mapping
    resp_map = {
        "none": 0,
        "room air": 0,
        "low-flow": 1,
        "nasal cannula": 1,
        "simple mask": 1,
        "high-flow": 2,
        "non-rebreather": 2,
        "cpap": 2,
        "bipap": 2,
        "ventilator": 3,
        "intubated": 3,
        "oscillator": 3,
        "hfov": 3,
    }
    param_scores["respiratory_support"] = parse_numeric_or_map(
        respiratory_support, resp_map, default=0
    )

    # Oxygen requirement mapping
    if oxygen_requirement is not None:
        if isinstance(oxygen_requirement, (int, float)):
            param_scores["oxygen_requirement"] = min(3, max(0, int(oxygen_requirement)))
        else:
            try:
                # Try to interpret as percentage
                o2_value = float(str(oxygen_requirement).replace("%", ""))
                if o2_value <= 28:
                    param_scores["oxygen_requirement"] = 0
                elif o2_value <= 40:
                    param_scores["oxygen_requirement"] = 1
                elif o2_value <= 60:
                    param_scores["oxygen_requirement"] = 2
                else:
                    param_scores["oxygen_requirement"] = 3
            except (ValueError, TypeError):
                # Interpret as descriptive text
                o2_map = {
                    "none": 0,
                    "room air": 0,
                    "ra": 0,
                    "21": 0,
                    "21%": 0,
                    "low": 1,
                    "minimal": 1,
                    "nasal cannula": 1,
                    "moderate": 2,
                    "high": 2,
                    "face mask": 2,
                    "non-rebreather": 2,
                    "very high": 3,
                    "critical": 3,
                    "100%": 3,
                }
                param_scores["oxygen_requirement"] = o2_map.get(
                    str(oxygen_requirement).lower(), 0
                )
    else:
        param_scores["oxygen_requirement"] = 0  # Assume room air if not specified

    # Cardiovascular support mapping
    cv_map = {
        "none": 0,
        "stable": 0,
        "fluid bolus": 1,
        "maintenance iv": 1,
        "single med": 1,
        "multiple meds": 2,
        "pressors": 2,
        "vasoactive": 2,
        "multiple pressors": 3,
        "unstable": 3,
        "ecmo": 3,
        "vad": 3,
    }
    param_scores["cardiovascular_support"] = parse_numeric_or_map(
        cardiovascular_support, cv_map, default=0
    )

    # Vitals frequency mapping
    vitals_map = {
        "q4h": 0,
        "q 4 hours": 0,
        "routine": 0,
        "q2h": 1,
        "q 2 hours": 1,
        "q1h": 2,
        "q 1 hour": 2,
        "hourly": 2,
        "continuous": 3,
        "q15min": 3,
        "q 15 minutes": 3,
    }
    param_scores["vitals_frequency"] = parse_numeric_or_map(
        vitals_frequency, vitals_map, default=0
    )

    # Map the rest of the parameters using a generic level map
    level_map = {
        "none": 0,
        "minimal": 0,
        "low": 0,
        "mild": 1,
        "basic": 1,
        "simple": 1,
        "moderate": 2,
        "intermediate": 2,
        "complex": 2,
        "high": 3,
        "severe": 3,
        "intensive": 3,
        "maximum": 3,
    }

    # Process remaining parameters
    for param in [
        "intervention_level",
        "invasive_lines",
        "medication_complexity",
        "nursing_dependency",
        "care_requirements",
        "patient_factors",
    ]:
        param_scores[param] = parse_numeric_or_map(
            all_params[param], level_map, default=0
        )

    # Calculate total score
    total_score = sum(param_scores.values())

    # Define acuity level thresholds
    cameo_thresholds = [
        (10, "Low Acuity", "Standard nurse-to-patient ratio"),
        (20, "Moderate Acuity", "Consider 1:2 nurse-to-patient ratio"),
        (27, "High Acuity", "1:1 nurse-to-patient ratio recommended"),
        (999, "Extreme Acuity", "1:1 nursing with additional support required"),
    ]

    acuity_level, nursing_recommendation = normalize_to_risk_level(
        total_score, cameo_thresholds
    )

    return {
        "score": total_score,
        "acuity_level": acuity_level,
        "nursing_recommendation": nursing_recommendation,
        "parameter_scores": param_scores,
    }


def calculate_prism3(vitals=None, labs=None, age_months=None, ventilated=False):
    """
    Calculate the Pediatric Risk of Mortality III (PRISM III) score

    PRISM III is a physiology-based scoring system that predicts mortality risk
    in pediatric intensive care units. It evaluates 17 physiological variables
    across multiple body systems to determine severity and risk of mortality.

    Args:
        vitals: Dictionary containing vital signs:
            - 'systolic_bp': Systolic blood pressure in mmHg
            - 'heart_rate': Heart rate in bpm
            - 'respiratory_rate': Respiratory rate in breaths/min
            - 'temperature': Temperature in Celsius
            - 'gcs': Glasgow Coma Scale (3-15)
            - 'pupils': Pupillary response ('reactive', 'fixed')
        labs: Dictionary containing lab values:
            - 'ph': Blood pH
            - 'pco2': PCO2 in mmHg
            - 'po2': PO2 in mmHg
            - 'glucose': Glucose in mg/dL
            - 'potassium': Potassium in mEq/L
            - 'creatinine': Creatinine in mg/dL
            - 'bun': BUN in mg/dL
            - 'wbc': White blood cell count in thousands/μL
            - 'pt': Prothrombin time (PT) in seconds
            - 'ptt': Partial thromboplastin time (PTT) in seconds
            - 'platelets': Platelet count in thousands/μL
        age_months: Age in months
        ventilated: Whether the patient is on mechanical ventilation

    Returns:
        Dictionary with total score, mortality risk, and subscores by system.
        Returns 'N/A' for score and all subscores if required parameters are missing.
    """
    # Define subscore keys for consistent NA responses
    subscore_keys = [
        "cardiovascular",
        "neurological",
        "acid_base",
        "hematologic",
        "other",
    ]

    # Check if vital signs dictionary is missing entirely
    if vitals is None:
        response = create_na_response(
            "PRISM III", ["vitals"], subscore_keys, include_action=False
        )
        response["mortality_risk"] = "Cannot calculate: vital signs missing"
        return response

    # Check if lab values dictionary is missing entirely
    if labs is None:
        response = create_na_response(
            "PRISM III", ["labs"], subscore_keys, include_action=False
        )
        response["mortality_risk"] = "Cannot calculate: laboratory values missing"
        return response

    # Check for minimum required vital signs
    required_vitals = ["systolic_bp", "heart_rate", "gcs"]
    missing_vitals = [
        vital
        for vital in required_vitals
        if vital not in vitals or vitals[vital] is None
    ]

    # Check for minimum required lab values
    required_labs = ["ph", "po2", "glucose", "potassium"]
    missing_labs = [
        lab for lab in required_labs if lab not in labs or labs[lab] is None
    ]

    # If critical parameters are missing, return N/A
    if missing_vitals or missing_labs:
        response = create_na_response(
            "PRISM III",
            missing_vitals + missing_labs,
            subscore_keys,
            include_action=False,
        )
        response["mortality_risk"] = "Cannot calculate: missing critical parameters"
        return response

    # Check if age is missing
    if age_months is None:
        response = create_na_response(
            "PRISM III", ["age_months"], subscore_keys, include_action=False
        )
        response["mortality_risk"] = "Cannot calculate: patient age is required"
        return response

    # Initialize subscores
    cardiovascular_score = 0
    neurological_score = 0
    acid_base_score = 0
    hematologic_score = 0
    other_score = 0

    # Cardiovascular scoring
    sbp = vitals.get("systolic_bp")
    hr = vitals.get("heart_rate")

    # Age-based thresholds for blood pressure
    # Different thresholds for infants (< 1 year), children (1-12 years), and adolescents (> 12 years)
    if age_months < 12:  # Infant
        if sbp < 40:
            cardiovascular_score += 7
        elif sbp < 55:
            cardiovascular_score += 3

        if hr < 90:
            cardiovascular_score += 3
        elif hr > 160:
            cardiovascular_score += 3
    elif age_months < 144:  # Child (1-12 years)
        if sbp < 50:
            cardiovascular_score += 7
        elif sbp < 65:
            cardiovascular_score += 3

        if hr < 70:
            cardiovascular_score += 3
        elif hr > 150:
            cardiovascular_score += 3
    else:  # Adolescent (> 12 years)
        if sbp < 60:
            cardiovascular_score += 7
        elif sbp < 75:
            cardiovascular_score += 3

        if hr < 55:
            cardiovascular_score += 3
        elif hr > 140:
            cardiovascular_score += 3

    # Neurological scoring
    gcs = vitals.get("gcs")
    pupils = vitals.get("pupils")

    if gcs <= 8:
        neurological_score += 5
    elif gcs <= 11:
        neurological_score += 2

    if pupils == "fixed" or pupils == "unreactive" or pupils == "nonreactive":
        neurological_score += 7

    # Acid-base and oxygenation scoring
    ph = labs.get("ph")
    pco2 = labs.get("pco2")
    po2 = labs.get("po2")

    if ph < 7.0:
        acid_base_score += 6
    elif ph < 7.3:
        acid_base_score += 2
    elif ph > 7.55:
        acid_base_score += 3

    if pco2 is not None:
        if pco2 > 75:
            acid_base_score += 3

    if ventilated:  # Different PO2 thresholds if ventilated
        if po2 < 42:
            acid_base_score += 6
        elif po2 < 50:
            acid_base_score += 3
    else:
        if po2 < 50:
            acid_base_score += 6
        elif po2 < 60:
            acid_base_score += 3

    # Metabolic scoring (part of 'other')
    glucose = labs.get("glucose")
    potassium = labs.get("potassium")
    creatinine = labs.get("creatinine")
    bun = labs.get("bun")

    if glucose > 200:
        other_score += 2
    elif glucose < 40:
        other_score += 8

    if potassium > 6.9:
        other_score += 3
    elif potassium < 3.0:
        other_score += 3

    # Age-based thresholds for creatinine
    if creatinine is not None:
        if age_months < 12 and creatinine > 0.85:
            other_score += 2
        elif age_months < 144 and creatinine > 0.90:
            other_score += 2
        elif creatinine > 1.30:
            other_score += 2

    if bun is not None:
        if bun > 40:
            other_score += 3

    # Hematologic scoring
    wbc = labs.get("wbc")
    pt = labs.get("pt")
    ptt = labs.get("ptt")
    platelets = labs.get("platelets")

    if wbc is not None:
        if wbc < 3.0:
            hematologic_score += 4

    if pt is not None and ptt is not None:
        if pt > 22 or ptt > 57:
            hematologic_score += 3

    if platelets is not None:
        if platelets < 50:
            hematologic_score += 4
        elif platelets < 100:
            hematologic_score += 2

    # Calculate total score
    total_score = (
        cardiovascular_score
        + neurological_score
        + acid_base_score
        + hematologic_score
        + other_score
    )

    # Define mortality risk thresholds
    prism_thresholds = [
        (5, "Very Low (<1%)", ""),
        (10, "Low (1-5%)", ""),
        (15, "Moderate (5-15%)", ""),
        (20, "High (15-30%)", ""),
        (999, "Very High (>30%)", ""),
    ]

    mortality_risk, _ = normalize_to_risk_level(total_score, prism_thresholds)

    return {
        "score": total_score,
        "mortality_risk": mortality_risk,
        "subscores": {
            "cardiovascular": cardiovascular_score,
            "neurological": neurological_score,
            "acid_base": acid_base_score,
            "hematologic": hematologic_score,
            "other": other_score,
        },
    }


# Example functions for demonstrating usage of the scoring systems
def example_pews():
    """Example usage of the Pediatric Early Warning Score"""
    result = calculate_pews(
        age_months=36,  # 3-year-old
        respiratory_rate=32,
        respiratory_effort="moderate",
        oxygen_requirement="low",
        heart_rate=135,
        capillary_refill=2.5,
        behavior="irritable",
    )

    print("\n🟢 PEWS Example:")
    print(f"Score: {result['score']} - {result['interpretation']}")
    print(f"Action: {result['action']}")
    print("Subscores:")
    for system, subscore in result["subscores"].items():
        print(f"  - {system.capitalize()}: {subscore}")

    return result


def example_trap():
    """Example usage of the Transport Risk Assessment in Pediatrics Score"""
    result = calculate_trap(
        respiratory_support="high-flow",
        respiratory_rate=25,
        work_of_breathing="moderate",
        oxygen_saturation=92,
        hemodynamic_stability="compensated",
        blood_pressure=85,
        heart_rate=130,
        neuro_status="altered",
        gcs=13,
        access_difficulty="yes",
        age_months=48,  # 4-year-old
    )

    print("\n🟠 TRAP Example:")
    print(f"Score: {result['score']} - {result['risk_level']}")
    print(f"Team Recommendation: {result['team_recommendation']}")
    print("Subscores:")
    for system, subscore in result["subscores"].items():
        print(f"  - {system.capitalize()}: {subscore}")

    return result


def example_cameo2():
    """Example usage of the CAMEO II Score"""
    result = calculate_cameo2(
        physiologic_instability="moderate",
        respiratory_support="nasal cannula",
        oxygen_requirement="low",
        cardiovascular_support="none",
        vitals_frequency="q2h",
        intervention_level="moderate",
        invasive_lines="peripheral iv",
        medication_complexity="moderate",
        nursing_dependency="moderate",
        care_requirements="increased",
        patient_factors="language barrier",
    )

    print("\n🟣 CAMEO II Example:")
    print(f"Score: {result['score']} - {result['acuity_level']}")
    print(f"Interpretation: {result['interpretation']}")
    print("Domain Scores:")
    for domain, score in result["domain_scores"].items():
        print(f"  - {domain.replace('_', ' ').capitalize()}: {score}/50")

    return result


def example_prism3():
    """Example usage of the PRISM III Score"""
    vitals = {"SBP": 85, "HR": 115, "GCS": 11, "pupillary_reactivity": "normal"}

    labs = {
        "pH": 7.25,
        "PaCO2": 48,
        "PaO2": 75,
        "FiO2": 0.4,
        "HCO3": 20,
        "glucose": 120,
        "potassium": 4.2,
        "creatinine": 0.6,
        "BUN": 15,
        "WBC": 8.5,
        "platelets": 180,
        "PT": 14,
        "PTT": 35,
    }

    result = calculate_prism3(
        vitals=vitals, labs=labs, age_months=60, ventilated=False  # 5-year-old
    )

    print("\n🔴 PRISM III Example:")
    print(f"Score: {result['score']} - {result['mortality_risk']}")
    print(f"Interpretation: {result['interpretation']}")
    print("Subscores:")
    for system, subscore in result["subscores"].items():
        print(f"  - {system.capitalize()}: {subscore}")

    return result


def calculate_queensland_non_trauma(
    resp_rate=None, HR=None, mental_status=None, SpO2=None, age_months=None
):
    """
    Calculate the Queensland Pediatric Non-Trauma Early Warning Score

    This system is used for early identification of pediatric patients at risk of deterioration
    in non-trauma settings, commonly used in Australia.

    Args:
        resp_rate: Respiratory rate in breaths per minute
        HR: Heart rate in beats per minute
        mental_status: 'alert', 'voice', 'pain', or 'unresponsive' (AVPU scale)
        SpO2: Oxygen saturation percentage
        age_months: Age in months (required for age-appropriate ranges)

    Returns:
        Dictionary with score, risk level, action recommendations, and subscores.
        Returns 'N/A' for score and all metrics if required parameters are missing.
    """
    # Check for required parameters
    required_params = {
        "resp_rate": resp_rate,
        "HR": HR,
        "mental_status": mental_status,
        "SpO2": SpO2,
        "age_months": age_months,
    }

    # Define subscore keys for consistent NA responses
    subscore_keys = [
        "respiratory_rate",
        "heart_rate",
        "mental_status",
        "oxygen_saturation",
    ]

    missing_params = [
        param for param, value in required_params.items() if value is None
    ]
    if missing_params:
        response = create_na_response(
            "Queensland Non-Trauma", missing_params, subscore_keys
        )
        response["age_category"] = "N/A"
        return response

    # Determine age category and thresholds
    age_categories = [
        (3, "Infant < 3 months", [20, 30, 40, 60, 80], [100, 120, 150, 180, 190]),
        (12, "Infant 3-12 months", [15, 25, 35, 50, 70], [90, 110, 130, 165, 180]),
        (48, "Child 1-4 years", [15, 20, 30, 40, 55], [80, 100, 120, 150, 170]),
        (144, "Child 4-12 years", [10, 15, 20, 30, 40], [70, 80, 100, 130, 150]),
        (float("inf"), "Child > 12 years", [8, 10, 15, 25, 30], [60, 70, 90, 120, 140]),
    ]

    # Find the appropriate age category
    for age_limit, category, rr_thresholds, hr_thresholds in age_categories:
        if age_months < age_limit:
            age_category = category
            break

    # Initialize subscores
    subscores = {}

    # Score respiratory rate
    rr_score = 0
    if resp_rate < rr_thresholds[0]:  # Extreme bradypnea
        rr_score = 4
    elif resp_rate <= rr_thresholds[1]:  # Moderate bradypnea
        rr_score = 2
    elif resp_rate <= rr_thresholds[2]:  # Normal
        rr_score = 0
    elif resp_rate <= rr_thresholds[3]:  # Moderate tachypnea
        rr_score = 2
    elif resp_rate <= rr_thresholds[4]:  # Severe tachypnea
        rr_score = 3
    else:  # Extreme tachypnea
        rr_score = 4

    subscores["respiratory_rate"] = rr_score

    # Score heart rate
    hr_score = 0
    if HR < hr_thresholds[0]:  # Extreme bradycardia
        hr_score = 4
    elif HR <= hr_thresholds[1]:  # Moderate bradycardia
        hr_score = 2
    elif HR <= hr_thresholds[2]:  # Normal
        hr_score = 0
    elif HR <= hr_thresholds[3]:  # Moderate tachycardia
        hr_score = 2
    elif HR <= hr_thresholds[4]:  # Severe tachycardia
        hr_score = 3
    else:  # Extreme tachycardia
        hr_score = 4

    subscores["heart_rate"] = hr_score

    # Score mental status (AVPU)
    subscores["mental_status"] = safe_get_from_map(mental_status, MENTAL_STATUS_MAP)

    # Score oxygen saturation
    spo2_score = 0
    if SpO2 >= 95:
        spo2_score = 0
    elif SpO2 >= 90:
        spo2_score = 1
    elif SpO2 >= 85:
        spo2_score = 2
    else:  # SpO2 < 85
        spo2_score = 3

    subscores["oxygen_saturation"] = spo2_score

    # Calculate total score
    total_score = sum(subscores.values())

    # Define risk thresholds
    queensland_thresholds = [
        (3, "Low Risk", "Continue routine care; reassess as needed"),
        (6, "Moderate Risk", "Increase observation frequency; consider medical review"),
        (9, "High Risk", "Urgent medical review; consider ICU consult"),
        (
            999,
            "Critical Risk",
            "Immediate medical intervention; ICU consult/transfer indicated",
        ),
    ]

    risk_level, action = normalize_to_risk_level(total_score, queensland_thresholds)

    return {
        "score": total_score,
        "risk_level": risk_level,
        "action": action,
        "age_category": age_category,
        "subscores": subscores,
    }


def calculate_queensland_trauma(
    mechanism=None, consciousness=None, airway=None, breathing=None, circulation=None
):
    """
    Calculate the Queensland Pediatric Trauma Score

    This scoring system is used for rapid assessment of trauma severity in pediatric patients,
    commonly used in Australian emergency settings.

    Args:
        mechanism: Trauma mechanism ('low', 'medium', 'high', 'very high')
        consciousness: Level of consciousness ('alert', 'voice', 'pain', 'unresponsive')
        airway: Airway status ('patent', 'maintainable', 'unmaintainable')
        breathing: Breathing status ('normal', 'distressed', 'severely compromised')
        circulation: Circulation status ('normal', 'reduced', 'severely compromised')

    Returns:
        Dictionary with score, risk level, and action recommendations.
        Returns 'N/A' if critical parameters are missing.
    """
    # Check for required parameters
    required_params = {
        "mechanism": mechanism,
        "consciousness": consciousness,
        "airway": airway,
        "breathing": breathing,
        "circulation": circulation,
    }

    # Define subscore keys for consistent NA responses
    subscore_keys = ["mechanism", "consciousness", "airway", "breathing", "circulation"]

    # All parameters are critical for this score
    missing_params = [
        param for param, value in required_params.items() if value is None
    ]
    if missing_params:
        return create_na_response("Queensland Trauma", missing_params, subscore_keys)

    # Initialize subscores
    subscores = {}

    # Score mechanism of injury
    mechanism_map = {
        "low": 0,
        "minor": 0,
        "fall < 1m": 0,
        "low velocity": 0,
        "medium": 1,
        "moderate": 1,
        "fall 1-3m": 1,
        "moderate velocity": 1,
        "high": 2,
        "severe": 2,
        "fall > 3m": 2,
        "high velocity": 2,
        "pedestrian": 2,
        "very high": 3,
        "extreme": 3,
        "ejection": 3,
        "fatality at scene": 3,
    }

    subscores["mechanism"] = safe_get_from_map(mechanism, mechanism_map)

    # Score level of consciousness (AVPU scale)
    subscores["consciousness"] = safe_get_from_map(consciousness, MENTAL_STATUS_MAP)

    # Score airway status
    airway_map = {
        "patent": 0,
        "clear": 0,
        "normal": 0,
        "maintainable": 1,
        "needs positioning": 1,
        "partial obstruction": 1,
        "unmaintainable": 2,
        "threatened": 2,
        "obstructed": 2,
        "intervention needed": 2,
    }

    subscores["airway"] = safe_get_from_map(airway, airway_map)

    # Score breathing status
    breathing_map = {
        "normal": 0,
        "unlabored": 0,
        "good air entry": 0,
        "distressed": 1,
        "moderate distress": 1,
        "increased work": 1,
        "severely compromised": 2,
        "severe distress": 2,
        "poor air entry": 2,
        "cyanotic": 2,
    }

    subscores["breathing"] = safe_get_from_map(breathing, breathing_map)

    # Score circulation status
    circulation_map = {
        "normal": 0,
        "good perfusion": 0,
        "capillary refill < 2s": 0,
        "reduced": 1,
        "delayed capillary refill": 1,
        "tachycardia": 1,
        "severely compromised": 2,
        "poor perfusion": 2,
        "hypotension": 2,
        "shock": 2,
    }

    subscores["circulation"] = safe_get_from_map(circulation, circulation_map)

    # Calculate total score
    total_score = sum(subscores.values())

    # Define risk thresholds
    trauma_thresholds = [
        (
            2,
            "Low Risk",
            "Consider discharge after appropriate observation and management",
        ),
        (
            5,
            "Moderate Risk",
            "Admit for observation and management; consider transfer if facilities limited",
        ),
        (8, "High Risk", "Stabilize and consider transfer to higher level of care"),
        (
            999,
            "Critical Risk",
            "Immediate resuscitation and transfer to pediatric trauma center",
        ),
    ]

    risk_level, action = normalize_to_risk_level(total_score, trauma_thresholds)

    return {
        "score": total_score,
        "risk_level": risk_level,
        "action": action,
        "subscores": subscores,
    }


def calculate_tps(
    respiratory_status=None, circulation_status=None, neurologic_status=None
):
    """
    Calculate the Transport Physiology Score (TPS)

    This score is used to assess physiological derangement during pediatric transport.
    It's designed to be quick to calculate with minimal parameters.

    Args:
        respiratory_status: Description of respiratory condition
        circulation_status: Description of circulatory status
        neurologic_status: Description of neurological status

    Returns:
        Dictionary with score, risk level, and transport recommendations.
        Returns 'N/A' if all parameters are missing.
    """
    # Define all parameters to check
    all_params = {
        "respiratory_status": respiratory_status,
        "circulation_status": circulation_status,
        "neurologic_status": neurologic_status,
    }

    # Define subscore keys for consistent NA responses
    subscore_keys = ["respiratory", "circulation", "neurologic"]

    # Check if all parameters are missing
    missing_params = [param for param, value in all_params.items() if value is None]
    if len(missing_params) == 3:  # All parameters missing
        return create_na_response(
            "TPS", missing_params, subscore_keys, include_interpretation=False
        )

    # Initialize subscores dictionary
    subscores = {}

    # Score respiratory status
    resp_map = {
        "normal": 0,
        "stable": 0,
        "no distress": 0,
        "mild": 1,
        "minimal": 1,
        "slight": 1,
        "moderate": 2,
        "significant": 2,
        "distress": 2,
        "severe": 3,
        "critical": 3,
        "respiratory failure": 3,
    }

    subscores["respiratory"] = (
        0
        if respiratory_status is None
        else safe_get_from_map(respiratory_status, resp_map)
    )

    # Score circulation status
    circ_map = {
        "normal": 0,
        "stable": 0,
        "good perfusion": 0,
        "mild": 1,
        "compensated": 1,
        "tachycardia": 1,
        "moderate": 2,
        "hypotension": 2,
        "poor perfusion": 2,
        "severe": 3,
        "decompensated": 3,
        "shock": 3,
    }

    subscores["circulation"] = (
        0
        if circulation_status is None
        else safe_get_from_map(circulation_status, circ_map)
    )

    # Score neurologic status
    neuro_map = {
        "normal": 0,
        "alert": 0,
        "appropriate": 0,
        "mild": 1,
        "irritable": 1,
        "agitated": 1,
        "altered": 1,
        "moderate": 2,
        "lethargic": 2,
        "confused": 2,
        "decreased responsiveness": 2,
        "severe": 3,
        "unresponsive": 3,
        "seizure": 3,
        "coma": 3,
    }

    subscores["neurologic"] = (
        0
        if neurologic_status is None
        else safe_get_from_map(neurologic_status, neuro_map)
    )

    # Calculate total score
    total_score = sum(subscores.values())

    # Define risk thresholds
    tps_thresholds = [
        (2, "Low Risk", "Standard transport team; routine monitoring"),
        (5, "Moderate Risk", "Consider advanced transport team; increased monitoring"),
        (
            999,
            "High Risk",
            "Critical care transport team required; continuous intensive monitoring",
        ),
    ]

    risk_level, transport_recommendation = normalize_to_risk_level(
        total_score, tps_thresholds
    )

    return {
        "score": total_score,
        "risk_level": risk_level,
        "transport_recommendation": transport_recommendation,
        "subscores": subscores,
    }


def calculate_chews(
    respiratory_rate=None,
    respiratory_effort=None,
    heart_rate=None,
    systolic_bp=None,
    capillary_refill=None,
    oxygen_therapy=None,
    oxygen_saturation=None,
    age_months=None,
):
    """
    Calculate the Children's Hospital Early Warning Score (CHEWS)

    This score is designed to identify clinical deterioration in hospitalized children.
    It includes multiple physiological parameters and is age-adjusted.

    Args:
        respiratory_rate: Breaths per minute
        respiratory_effort: Respiratory effort assessment ('normal', 'mild', 'moderate', 'severe')
        heart_rate: Beats per minute
        systolic_bp: Systolic blood pressure
        capillary_refill: Capillary refill time in seconds
        oxygen_therapy: Type of oxygen support ('none', 'low flow', 'high flow', 'ventilator')
        oxygen_saturation: Oxygen saturation percentage
        age_months: Age in months (for age-appropriate thresholds)

    Returns:
        Dictionary with score, alert level, and action recommendations.
        Returns 'N/A' for score if critical parameters are missing.
    """
    # Check for critical parameters - these are the core vitals that cannot be reasonably assumed
    critical_params = {"respiratory_rate": respiratory_rate, "heart_rate": heart_rate}
    missing_critical = [
        param for param, value in critical_params.items() if value is None
    ]

    # Check all missing parameters
    all_params = {
        "respiratory_rate": respiratory_rate,
        "respiratory_effort": respiratory_effort,
        "heart_rate": heart_rate,
        "systolic_bp": systolic_bp,
        "capillary_refill": capillary_refill,
        "oxygen_therapy": oxygen_therapy,
        "oxygen_saturation": oxygen_saturation,
    }
    missing_params = [param for param, value in all_params.items() if value is None]

    # Define subscore keys for consistent NA responses
    subscore_keys = [
        "respiratory_rate",
        "respiratory_effort",
        "heart_rate",
        "systolic_bp",
        "capillary_refill",
        "oxygen_therapy",
        "oxygen_saturation",
    ]

    # Check for missing critical parameters
    missing_critical = [
        param for param, value in critical_params.items() if value is None
    ]
    if missing_critical:
        response = create_na_response("CHEWS", missing_critical, subscore_keys)
        response["alert_level"] = "Cannot calculate: missing critical parameters"
        response["normal_ranges"] = {}
        return response

    # Get reference ranges for this age
    ranges = get_age_based_ranges(age_months)
    hr_min, hr_max = ranges["heart_rate"]
    rr_min, rr_max = ranges["respiratory_rate"]

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
    subscores["respiratory_effort"] = safe_get_from_map(
        respiratory_effort, RESPIRATORY_EFFORT_MAP
    )

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
        (
            4,
            "Medium Alert Level",
            "Increase assessment frequency; consider medical review",
        ),
        (
            6,
            "High Alert Level",
            "Urgent medical review required; consider PICU consult",
        ),
        (
            999,
            "Critical Alert Level",
            "Immediate medical intervention; PICU consult/transfer indicated",
        ),
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
            "systolic_bp": f"~{int(normal_sbp)} mmHg",
        },
    }


def example_queensland():
    """Example usage of the Queensland Pediatric Non-Trauma Early Warning Score"""
    result = calculate_queensland_non_trauma(
        resp_rate=28,
        HR=125,
        mental_status="voice",
        SpO2=94,
        age_months=36,  # 3-year-old
    )

    print("\n🟡 Queensland Pediatric Non-Trauma Example:")
    print(f"Score: {result['score']} - {result['risk_level']}")
    print(f"Action: {result['action']}")
    print(f"Age Category: {result['age_category']}")
    print("Subscores:")
    for param, subscore in result["subscores"].items():
        print(f"  - {param.replace('_', ' ').capitalize()}: {subscore}")

    return result


def example_tps():
    """Example usage of the Transport Physiology Score"""
    result = calculate_tps(
        respiratory_status="moderate",
        circulation_status="normal",
        neurologic_status="altered",
    )

    print("\n🔵 Transport Physiology Score Example:")
    print(f"Score: {result['score']} - {result['risk_level']}")
    print(f"Transport Recommendation: {result['transport_recommendation']}")
    print("Subscores:")
    for system, subscore in result["subscores"].items():
        print(f"  - {system.capitalize()}: {subscore}")

    return result


def example_chews():
    """Example usage of the Children's Hospital Early Warning Score"""
    result = calculate_chews(
        respiratory_rate=25,
        respiratory_effort="mild",
        heart_rate=130,
        systolic_bp=95,
        capillary_refill=2.5,
        oxygen_therapy="low flow",
        oxygen_saturation=94,
        age_months=48,  # 4-year-old
    )

    print("\n⚫ CHEWS Example:")
    print(f"Score: {result['score']} - {result['alert_level']}")
    print(f"Action: {result['action']}")
    print("Normal Ranges:")
    for param, range_val in result["normal_ranges"].items():
        print(f"  - {param.replace('_', ' ').capitalize()}: {range_val}")
    print("Subscores:")
    for param, subscore in result["subscores"].items():
        print(f"  - {param.replace('_', ' ').capitalize()}: {subscore}")

    return result


if __name__ == "__main__":
    print("=== Pediatric Severity Scoring Systems Examples ===")
    example_pews()
    example_trap()
    example_cameo2()
    example_prism3()
    example_queensland()
    example_tps()
    example_chews()
