"""
Simulates LLM-based parsing of unstructured patient text.

This module provides functionality to extract structured information from
raw clinical notes, including potential medical conditions, vital signs (via regex),
location cues, and a brief summary. It is intended as a placeholder for
more sophisticated NLP/LLM capabilities.
"""
import re
from typing import Dict, List

# (Keep PREDEFINED_KEYWORDS_TO_CONDITIONS from previous version)
PREDEFINED_KEYWORDS_TO_CONDITIONS: Dict[str, List[str]] = {
    "cardiac": ["chest pain", "palpitations", "arrhythmia", "bradycardia", "tachycardia", "heart attack", "myocardial infarction"],
    "respiratory": ["shortness of breath", "sob", "difficulty breathing", "wheezing", "coughing blood", "copd exacerbation", "asthma attack"],
    "neurological": ["stroke", "tia", "seizure", "severe headache", "altered mental status", "ams", "dizziness", "sudden weakness"],
    "trauma": ["fall", "motor vehicle accident", "mva", "fracture", "major burn", "deep laceration", "head injury"],
    "sepsis": ["fever", "hypotension", "suspected infection", "septic shock", "rigors"],
    "psychiatric": ["suicidal ideation", "homicidal ideation", "acute psychosis", "severe agitation"],
    "pediatric_emergency": ["infant distress", "high fever child", "pediatric seizure", "neonate", "bronchiolitis", "rsv"] 
    # Add more as needed
}

# Basic regex for vital signs (examples, can be expanded)
# IMPORTANT: These are simple regex patterns for simulation and not robust for production use.
# A true LLM would handle variations, context, and negation much more effectively.
VITAL_SIGN_PATTERNS = {
    "bp": r"(?:bp|blood pressure)\s*:?\s*(\d{2,3}\s*/\s*\d{2,3})",
    "hr": r"(?:hr|heart rate|pulse)\s*:?\s*(\d{2,3})",
    "rr": r"(?:rr|respiratory rate)\s*:?\s*(\d{1,2})",
    "o2_sat": r"(?:o2|sats|oxygen saturation)\s*:?\s*(\d{1,3})%?"
}

# Basic regex for location cues (examples)
# IMPORTANT: These are simple regex patterns for simulation and not robust for production use.
LOCATION_CUE_PATTERNS = [
    r"at\s(?:the\s)?(?:corner of\s)?([\w\s.,#\-\d]+?)(?:\sand\s([\w\s.,#\-\d]+?))?(?=[,.?!]|$|\s[A-Z]{2}\s\d{5})", # "at corner of X and Y", "at X", "at 123 Main St"
    r"near\s(?:the\s)?([\w\s.,#\-\d]+?)(?=[,.?!]|$|\s[A-Z]{2}\s\d{5})" # "near X", "near 123 Main St"
]

def parse_patient_text(text: str) -> Dict:
    """
    Parses raw patient text to extract keywords, potential conditions,
    simulated vital signs, location cues, and a raw summary.

    IMPORTANT: The vital signs and location cue extractions are regex-based
    simulations of what a more sophisticated LLM would achieve. They are
    not robust for production environments.

    Args:
        text: The raw unstructured patient text (e.g., from clinical notes).

    Returns:
        A dictionary containing the extracted information:
            - "identified_keywords": List of keywords found in the text.
            - "potential_conditions": List of potential medical conditions inferred
                                      from keywords.
            - "extracted_vital_signs": Dictionary of vital signs extracted via regex.
            - "mentioned_location_cues": List of location-related phrases found.
            - "raw_text_summary": A brief summary of the input text (e.g., first
                                  two sentences).
    """
    if not text:
        return {
            "identified_keywords": [], "potential_conditions": [],
            "extracted_vital_signs": {}, "mentioned_location_cues": [],
            "raw_text_summary": ""
        }

    text_lower = text.lower() # Used for keyword matching
    
    # 1. Keyword-based condition identification (from previous version)
    identified_keywords: List[str] = []
    potential_conditions: List[str] = []
    for condition, keywords in PREDEFINED_KEYWORDS_TO_CONDITIONS.items():
        for keyword in keywords:
            if keyword.lower() in text_lower: # keyword.lower() ensures consistency if keywords have mixed case
                identified_keywords.append(keyword) # Store original casing of keyword for clarity
                if condition not in potential_conditions:
                    potential_conditions.append(condition)
    
    # 2. Vital Signs Extraction (Regex-based simulation)
    extracted_vital_signs: Dict[str, str] = {}
    # Using original text `text` for vital signs to preserve case if needed, though patterns are IGNORECASE
    for vital, pattern in VITAL_SIGN_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            extracted_vital_signs[vital] = match.group(1).strip()

    # 3. Location Cues Extraction (Regex-based simulation)
    mentioned_location_cues: List[str] = []
    # Using original text `text` for location cues
    for pattern in LOCATION_CUE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match_group in matches:
            # findall returns tuples if there are capture groups in the pattern.
            # We join the parts of the tuple that are not None or empty.
            # Example: for "at corner of X and Y", match_group might be ('X', 'Y')
            # For "at X", match_group might be ('X', '') or ('X', None)
            # For "near X", match_group is a string if no internal groups, or a tuple with one element.
            if isinstance(match_group, tuple):
                full_match = " ".join(filter(None, match_group)).strip()
            else: # It's a direct string match (e.g. if pattern had no capture groups or only one)
                full_match = match_group.strip()
            
            if full_match:
                mentioned_location_cues.append(full_match)
    
    # 4. Raw Text Summary (simple placeholder: first two sentences)
    # Split by common sentence terminators followed by whitespace.
    # Using original text `text` to preserve original casing in summary.
    summary_sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    raw_text_summary = " ".join(summary_sentences[:2]) # Take first two "sentences"

    return {
        "identified_keywords": sorted(list(set(identified_keywords))),
        "potential_conditions": sorted(list(set(potential_conditions))),
        "extracted_vital_signs": extracted_vital_signs,
        "mentioned_location_cues": sorted(list(set(mentioned_location_cues))), # Deduplicate and sort
        "raw_text_summary": raw_text_summary.strip()
    }

# Future Consideration:
# A higher-level function could be developed to take raw text (e.g., from a dispatch call)
# and attempt to populate a more structured PatientData model. This function might utilize
# parse_patient_text as a first pass, and then apply more sophisticated logic,
# potentially calling out to actual LLM APIs for robust NLP tasks like Named Entity Recognition (NER),
# relation extraction, and more nuanced summarization.
#
# Example:
# from src.core.models import PatientData, Location
#
# def convert_text_to_structured_patient_data(text: str) -> PatientData:
#     parsed_info = parse_patient_text(text)
#
#     # This would be a very simplified mapping and would need actual LLM/NLP
#     # to reliably convert free text to structured data.
#     patient_id = "temp_id_" + str(hash(text)) # Placeholder
#     chief_complaint = parsed_info["raw_text_summary"] # Or try to get from specific keywords
#     clinical_history = text # Or a more refined summary from LLM
#
#     # Vital signs mapping - direct if keys match, else needs more logic
#     vital_signs = parsed_info["extracted_vital_signs"]
#
#     # Labs would typically not come from initial dispatch text, but from actual lab results
#     labs = {} 
#
#     # Location: This is highly complex. Location cues are just hints.
#     # A real system might use geocoding services based on these cues.
#     # For now, if "mentioned_location_cues" has something, we just note it.
#     # Actual Location object requires lat/lon.
#     # current_location_description = "; ".join(parsed_info["mentioned_location_cues"])
#     # This is just a placeholder for where more advanced location processing would go.
#     # current_location = Location(latitude=0.0, longitude=0.0) # Dummy location
#
#     return PatientData(
#         patient_id=patient_id,
#         chief_complaint=chief_complaint,
#         clinical_history=clinical_history, # This would ideally be a structured history
#         vital_signs=vital_signs,
#         labs=labs,
#         # current_location=current_location # Requires actual geocoding
#         # The PatientData model expects a Location object for current_location,
#         # which has lat/lon. The text parser currently only gives textual cues.
#         # This part needs to be thought out - perhaps PatientData gets location later,
#         # or this parser only provides cues for a geocoding step.
#     )
#
# Note: The above `convert_text_to_structured_patient_data` is conceptual and NOT part of the
# current subtask's core implementation but serves as a thought exercise for future work.
# The primary goal of this subtask is the enhancement of `parse_patient_text`.

def determine_care_level(patient_data):
    """
    Determines the appropriate care level for a patient based on vital signs and clinical information.
    
    Args:
        patient_data: PatientData object with patient information
        
    Returns:
        String representing the care level ("General", "ICU", "NICU", etc.)
    """
    # Default care level
    care_level = "General"
    
    # Extract vital signs
    vital_signs = getattr(patient_data, "vital_signs", {})
    
    # Check for critical vital signs that would indicate ICU need
    hr = vital_signs.get("hr", "")
    if hr and hr.isdigit():
        hr_val = int(hr)
        if hr_val > 140 or hr_val < 50:  # Extreme heart rate
            care_level = "ICU"
    
    rr = vital_signs.get("rr", "")
    if rr and rr.isdigit():
        rr_val = int(rr)
        if rr_val > 30 or rr_val < 10:  # Extreme respiratory rate
            care_level = "ICU"
    
    o2_sat = vital_signs.get("o2_sat", "")
    if o2_sat and o2_sat.replace("%", "").isdigit():
        o2_val = int(o2_sat.replace("%", ""))
        if o2_val < 90:  # Low oxygen saturation
            care_level = "ICU"
    
    # Check clinical history for ICU indicators
    clinical_history = getattr(patient_data, "clinical_history", "").lower()
    icu_keywords = ["sepsis", "respiratory failure", "cardiac arrest", "stroke", "head trauma", 
                   "intubated", "ventilator", "shock", "unconscious", "multiple trauma"]
    
    for keyword in icu_keywords:
        if keyword in clinical_history:
            care_level = "ICU"
            break
    
    # Check for NICU needs (neonates)
    if "neonate" in clinical_history or "newborn" in clinical_history or "premature" in clinical_history:
        care_level = "NICU"
    
    return care_level
