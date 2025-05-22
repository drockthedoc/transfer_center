# Multi-Step Prompting Chain Documentation

This document provides a detailed breakdown of the multi-step prompting process used in the Transfer Center application, showing the prompts sent to the LLM and the expected chain of reasoning.

## Overview of the Four-Step Process

1. **Entity Extraction**: Extract structured clinical entities from the raw vignette
2. **Specialty Assessment**: Determine which medical specialties are needed
3. **Exclusion Criteria Evaluation**: Check if any exclusion criteria are met
4. **Final Recommendation**: Synthesize findings into a care level recommendation

## Complete Prompts and Expected Responses

### Step 1: Entity Extraction

**Prompt Template:**
```
You are an expert clinical information extractor. Extract all relevant clinical information 
from the following patient vignette. Think step-by-step and be thorough, but only include information 
that is explicitly mentioned in the text.

Format your response as a JSON object with the following structure:
{
  "symptoms": [list of symptoms mentioned],
  "medical_problems": [list of medical problems or conditions mentioned],
  "medications": [list of medications mentioned],
  "vital_signs": {dictionary of vital signs with values},
  "demographics": {
    "age": patient age if mentioned,
    "weight": patient weight if mentioned (in kg),
    "sex": patient sex if mentioned
  },
  "medical_history": relevant past medical history,
  "clinical_context": additional clinical context like location, transport mode
}

Extract clinical information from this patient vignette:

[PATIENT_VIGNETTE]
```

**Expected Response Format:**
```json
{
  "symptoms": ["symptom1", "symptom2"],
  "medical_problems": ["problem1", "problem2"],
  "medications": ["medication1", "medication2"],
  "vital_signs": {
    "hr": "value",
    "bp": "value",
    "rr": "value",
    "temp": "value",
    "o2": "value"
  },
  "demographics": {
    "age": "value",
    "weight": "value",
    "sex": "value"
  },
  "medical_history": "Relevant history text",
  "clinical_context": "Additional context"
}
```

**Chain of Reasoning:**
1. Identify explicit symptoms mentioned in the text
2. Identify medical problems or conditions
3. Extract medication information
4. Extract vital signs and normalize their format
5. Extract demographic information
6. Identify relevant past medical history
7. Note any additional clinical context

### Step 2: Specialty Assessment

**Prompt Template:**
```
You are an expert triage physician. Your task is to assess what medical specialties might be needed 
based on the clinical information provided. Think step-by-step about each potential specialty need.

Format your response as a JSON object with the following structure:
{
  "identified_specialties_needed": [
    {
      "specialty_name": "name of the specialty",
      "likelihood_score": numerical score from 0-100 indicating confidence,
      "supporting_evidence": "text explaining why this specialty is needed"
    },
    {...}
  ]
}

Based on these extracted clinical entities:

[EXTRACTED_ENTITIES_JSON]

And these specialty need indicators:
- cardiology: heart, cardiac, chest pain, arrhythmia, murmur
- neurology: seizure, stroke, headache, neurological, brain
- pulmonology: respiratory, breathing, asthma, pneumonia, lungs
- neonatology: newborn, premature, neonate, NICU
- orthopedics: fracture, bone, joint, sprain, musculoskeletal
- gastroenterology: abdominal pain, vomiting, diarrhea, GI bleed, liver
- endocrinology: diabetes, thyroid, hormone, glucose
- infectious disease: infection, sepsis, meningitis, cellulitis
- hematology/oncology: cancer, leukemia, anemia, bleeding, oncology
- psychiatry: psychiatric, depression, anxiety, mental health, suicide

Identify which specialties might be needed for this patient. For each specialty, provide a likelihood score (0-100) and supporting evidence from the clinical information.
```

**Expected Response Format:**
```json
{
  "identified_specialties_needed": [
    {
      "specialty_name": "Specialty1",
      "likelihood_score": 95,
      "supporting_evidence": "Evidence for why this specialty is needed"
    },
    {
      "specialty_name": "Specialty2",
      "likelihood_score": 60,
      "supporting_evidence": "Evidence for why this specialty is needed"
    }
  ]
}
```

**Chain of Reasoning:**
1. Analyze extracted entities to identify relevant medical issues
2. For each potential specialty, assess if there are indicators present
3. Consider primary, secondary, and tertiary specialty needs
4. Assign likelihood scores based on the strength of the evidence
5. Provide specific supporting evidence from the clinical information

### Step 3: Exclusion Criteria Evaluation

**Prompt Template:**
```
You are an expert transfer center physician. Your task is to evaluate whether this patient meets any 
exclusion criteria for transfer. Think step-by-step for each criterion.

Format your response as a JSON object with the following structure:
{
  "exclusion_criteria_evaluation": [
    {
      "exclusion_rule_id": "identifier of the exclusion rule",
      "rule_text": "full text of the exclusion rule",
      "status": "one of: 'likely_met', 'likely_not_met', 'uncertain'",
      "confidence_score": numerical score from 0-100,
      "evidence_from_vignette": "text explaining the evidence for this status determination"
    },
    {...}
  ]
}

Based on these extracted clinical entities:

[EXTRACTED_ENTITIES_JSON]

Evaluate whether the patient meets any of the following exclusion criteria:

[NUMBERED_EXCLUSION_CRITERIA_LIST]

For each numbered exclusion criterion, determine if it is 'likely_met', 'likely_not_met', or 'uncertain' based on the clinical information.
Provide a confidence score (0-100) for your determination and cite specific evidence from the clinical information.
```

**Expected Response Format:**
```json
{
  "exclusion_criteria_evaluation": [
    {
      "exclusion_rule_id": "1",
      "rule_text": "Full text of rule 1",
      "status": "likely_met",
      "confidence_score": 90,
      "evidence_from_vignette": "Evidence from the clinical information"
    },
    {
      "exclusion_rule_id": "2",
      "rule_text": "Full text of rule 2",
      "status": "likely_not_met",
      "confidence_score": 85,
      "evidence_from_vignette": "Evidence from the clinical information"
    }
  ]
}
```

**Chain of Reasoning:**
1. For each exclusion criterion, review the extracted clinical entities
2. Compare patient's condition against each specific exclusion rule
3. Determine if the criterion is likely met, not met, or uncertain
4. Assign a confidence score based on the available information
5. Cite specific evidence from the vignette supporting the determination

### Step 4: Final Recommendation

**Prompt Template:**
```
You are an expert transfer center physician making a final recommendation for patient transfer. 
Your task is to synthesize all the analysis done so far and recommend an appropriate care level.

Format your response as a JSON object with the following structure:
{
  "recommended_care_level": "one of: 'General', 'ICU', 'PICU', 'NICU'",
  "confidence": numerical score from 0-100,
  "explanation": "text explaining the overall recommendation"
}

Based on the combined analysis:

[COMBINED_ANALYSIS_JSON]

Determine the most appropriate care level for this patient. Consider the clinical entities, specialty needs, and exclusion criteria evaluations.
Provide a confidence score (0-100) for your recommendation and explain your reasoning in detail.
```

**Expected Response Format:**
```json
{
  "recommended_care_level": "PICU",
  "confidence": 95,
  "explanation": "Detailed explanation of the recommendation"
}
```

**Chain of Reasoning:**
1. Review all information from previous steps
2. Consider the severity of the patient's condition
3. Evaluate the specialty needs and their urgency
4. Consider any met exclusion criteria
5. Determine the most appropriate care level
6. Provide a confidence score for the recommendation
7. Explain the reasoning in detail

## Example Analysis Chain

For a real-world example of how this chain works, consider a 3-year-old with respiratory distress:

1. **Entity Extraction** identifies symptoms (increased work of breathing, fever), vital signs (tachypnea, tachycardia), and relevant history (prematurity, previous PICU admission)

2. **Specialty Assessment** identifies pulmonology as primary need (95% likelihood) with supporting evidence

3. **Exclusion Criteria Evaluation** determines if any campus-specific exclusions apply

4. **Final Recommendation** recommends PICU level care with explanation about respiratory needs and risk factors

This multi-step process ensures thorough analysis and transparent reasoning that can be reviewed by clinical staff.
