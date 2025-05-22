# Actual Multi-Step Prompting Example

This document captures the verbatim exchange between our system and the LLM for a clinical vignette analysis using the multi-step prompting process.

## Clinical Vignette Used

```
3-year-old male presenting with high fever (39.5°C), increased work of breathing,
and decreased oral intake for the past 2 days. HR 145, RR 35, BP 90/60, SpO2 93% on RA.
History of prematurity at 32 weeks, previous RSV bronchiolitis at 6 months requiring
PICU admission and brief HFNC support. Currently on albuterol and ipratropium nebs
with minimal improvement.
```

## Step 1: Entity Extraction

### Prompt Sent to LLM:
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

3-year-old male presenting with high fever (39.5°C), increased work of breathing,
and decreased oral intake for the past 2 days. HR 145, RR 35, BP 90/60, SpO2 93% on RA.
History of prematurity at 32 weeks, previous RSV bronchiolitis at 6 months requiring
PICU admission and brief HFNC support. Currently on albuterol and ipratropium nebs
with minimal improvement.
```

### LLM Response:
```json
{
  "symptoms": [
    "high fever (39.5°C)",
    "increased work of breathing",
    "decreased oral intake"
  ],
  "medical_problems": [
    "history of prematurity at 32 weeks",
    "previous RSV bronchiolitis at 6 months requiring PICU admission and brief HFNC support",
    "respiratory distress"
  ],
  "medications": [
    "albuterol nebulizers",
    "ipratropium nebulizers"
  ],
  "vital_signs": {
    "heart rate": "145",
    "respiratory rate": "35",
    "blood pressure": "90/60",
    "oxygen saturation": "93% on room air (RA)"
  },
  "demographics": {
    "age": "3 years",
    "weight": null,
    "sex": "male"
  },
  "medical_history": "History of prematurity at 32 weeks, previous RSV bronchiolitis at 6 months requiring PICU admission and brief HFNC support.",
  "clinical_context": "Currently on albuterol and ipratropium nebs with minimal improvement. Symptoms present for the past 2 days."
}
```

## Step 2: Specialty Assessment

### Prompt Sent to LLM:
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

{
  "symptoms": [
    "high fever (39.5°C)",
    "increased work of breathing",
    "decreased oral intake"
  ],
  "medical_problems": [
    "history of prematurity at 32 weeks",
    "previous RSV bronchiolitis at 6 months requiring PICU admission and brief HFNC support",
    "respiratory distress"
  ],
  "medications": [
    "albuterol nebulizers",
    "ipratropium nebulizers"
  ],
  "vital_signs": {
    "heart rate": "145",
    "respiratory rate": "35",
    "blood pressure": "90/60",
    "oxygen saturation": "93% on room air (RA)"
  },
  "demographics": {
    "age": "3 years",
    "weight": null,
    "sex": "male"
  },
  "medical_history": "History of prematurity at 32 weeks, previous RSV bronchiolitis at 6 months requiring PICU admission and brief HFNC support.",
  "clinical_context": "Currently on albuterol and ipratropium nebs with minimal improvement. Symptoms present for the past 2 days."
}

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

### LLM Response:
```json
{
  "identified_specialties_needed": [
    {
      "specialty_name": "Pulmonology",
      "likelihood_score": 95,
      "supporting_evidence": "Patient presents with respiratory distress (RR 35), increased work of breathing, and decreased oxygen saturation (93% on RA). History includes prematurity and previous RSV bronchiolitis, suggesting underlying respiratory vulnerability. Current presentation requires expert management of respiratory failure."
    },
    {
      "specialty_name": "Neonatology",
      "likelihood_score": 70,
      "supporting_evidence": "Patient has a history of prematurity at 32 weeks, which often leads to long-term respiratory issues. Previous severe RSV bronchiolitis requiring PICU admission and HFNC support indicates a history of significant respiratory illness common in premature infants. Neonatology expertise may be valuable given this background."
    },
    {
      "specialty_name": "Infectious Disease",
      "likelihood_score": 60,
      "supporting_evidence": "Patient presents with respiratory distress and fever (39.5°C), raising concern for a respiratory infection (e.g., pneumonia, severe viral illness). History of prematurity increases susceptibility to infections. Infectious disease consultation may be needed to identify the pathogen and guide antimicrobial therapy."
    },
    {
      "specialty_name": "Cardiology",
      "likelihood_score": 20,
      "supporting_evidence": "Patient has tachycardia (HR 145) and respiratory distress. While primarily respiratory, cardiac involvement cannot be entirely excluded in severe illness. Cardiology consultation is less likely but may be considered if cardiac dysfunction is suspected or if there are specific cardiac findings."
    }
  ]
}
```

## Step 3: Exclusion Criteria Evaluation

### Prompt Sent to LLM:
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

{
  "symptoms": [
    "high fever (39.5°C)",
    "increased work of breathing",
    "decreased oral intake"
  ],
  "medical_problems": [
    "history of prematurity at 32 weeks",
    "previous RSV bronchiolitis at 6 months requiring PICU admission and brief HFNC support",
    "respiratory distress"
  ],
  "medications": [
    "albuterol nebulizers",
    "ipratropium nebulizers"
  ],
  "vital_signs": {
    "heart rate": "145",
    "respiratory rate": "35",
    "blood pressure": "90/60",
    "oxygen saturation": "93% on room air (RA)"
  },
  "demographics": {
    "age": "3 years",
    "weight": null,
    "sex": "male"
  },
  "medical_history": "History of prematurity at 32 weeks, previous RSV bronchiolitis at 6 months requiring PICU admission and brief HFNC support.",
  "clinical_context": "Currently on albuterol and ipratropium nebs with minimal improvement. Symptoms present for the past 2 days."
}

Evaluate whether the patient meets any of the following exclusion criteria:

#1. GENERAL: Patients requiring active cardiopulmonary resuscitation
#2. GENERAL: Patients with unstable airway or requiring intubation during transport
#3. GENERAL: Patients with severe respiratory distress or SpO2 <90% on maximal supplemental oxygen
#4. GENERAL: Hemodynamically unstable patients requiring continuous vasopressor support
#5. PULMONARY: Patients requiring ECMO or candidates for ECMO evaluation
#6. PULMONARY: Patients with severe respiratory acidosis (pH <7.25 with elevated pCO2)
#7. NEUROLOGY: Patients with uncontrolled status epilepticus
#8. NEUROLOGY: Patients with acute stroke requiring thrombectomy or tPA administration
#9. TRAUMA: Patients with traumatic injuries requiring immediate surgical intervention
#10. TRAUMA: Patients with unstable pelvic fractures or active internal bleeding

For each numbered exclusion criterion, determine if it is 'likely_met', 'likely_not_met', or 'uncertain' based on the clinical information.
Provide a confidence score (0-100) for your determination and cite specific evidence from the clinical information.
```

### LLM Response:
```
I'll evaluate each exclusion criterion based on the provided clinical information:

{
  "exclusion_criteria_evaluation": [
    {
      "exclusion_rule_id": "1",
      "rule_text": "Patients requiring active cardiopulmonary resuscitation",
      "status": "likely_not_met",
      "confidence_score": 95,
      "evidence_from_vignette": "The patient has vital signs documented (HR 145, RR 35, BP 90/60, SpO2 93%) and is described as receiving nebulizer treatments. There is no mention of cardiac arrest or CPR being performed, suggesting the patient has a pulse and spontaneous circulation."
    },
    {
      "exclusion_rule_id": "2",
      "rule_text": "Patients with unstable airway or requiring intubation during transport",
      "status": "likely_not_met",
      "confidence_score": 85,
      "evidence_from_vignette": "While the patient has increased work of breathing, they are maintaining an oxygen saturation of 93% on room air and are receiving nebulizer treatments (albuterol and ipratropium). There is no mention of impending respiratory failure, stridor, or need for intubation."
    },
    {
      "exclusion_rule_id": "3",
      "rule_text": "Patients with severe respiratory distress or SpO2 <90% on maximal supplemental oxygen",
      "status": "likely_not_met",
      "confidence_score": 80,
      "evidence_from_vignette": "The patient has increased work of breathing but maintains SpO2 of 93% on room air (not requiring supplemental oxygen). While the patient has tachypnea (RR 35) indicating respiratory distress, they are not described as having severe distress and are maintaining adequate oxygenation without supplemental oxygen."
    },
    {
      "exclusion_rule_id": "4",
      "rule_text": "Hemodynamically unstable patients requiring continuous vasopressor support",
      "status": "likely_not_met",
      "confidence_score": 90,
      "evidence_from_vignette": "The patient has a documented blood pressure of 90/60, which is likely appropriate for a 3-year-old, and there is no mention of hypotension, shock, or vasopressor support being required."
    },
    {
      "exclusion_rule_id": "5",
      "rule_text": "Patients requiring ECMO or candidates for ECMO evaluation",
      "status": "likely_not_met",
      "confidence_score": 95,
      "evidence_from_vignette": "The patient has respiratory symptoms but is maintaining adequate oxygenation (93% on room air) and there is no mention of severe respiratory failure or cardiac failure that would necessitate ECMO consideration."
    },
    {
      "exclusion_rule_id": "6",
      "rule_text": "Patients with severe respiratory acidosis (pH <7.25 with elevated pCO2)",
      "status": "uncertain",
      "confidence_score": 50,
      "evidence_from_vignette": "No blood gas results are provided in the clinical information. The patient has tachypnea (RR 35) which could be compensating for acidosis, but there's insufficient information to determine if respiratory acidosis is present."
    },
    {
      "exclusion_rule_id": "7",
      "rule_text": "Patients with uncontrolled status epilepticus",
      "status": "likely_not_met",
      "confidence_score": 95,
      "evidence_from_vignette": "There is no mention of seizures or neurological symptoms in the clinical information."
    },
    {
      "exclusion_rule_id": "8",
      "rule_text": "Patients with acute stroke requiring thrombectomy or tPA administration",
      "status": "likely_not_met",
      "confidence_score": 95,
      "evidence_from_vignette": "There is no mention of neurological symptoms, stroke symptoms, or neurological deficits in the clinical information."
    },
    {
      "exclusion_rule_id": "9",
      "rule_text": "Patients with traumatic injuries requiring immediate surgical intervention",
      "status": "likely_not_met",
      "confidence_score": 95,
      "evidence_from_vignette": "There is no mention of trauma or injuries in the clinical information. The presentation appears to be medical (respiratory) in nature."
    },
    {
      "exclusion_rule_id": "10",
      "rule_text": "Patients with unstable pelvic fractures or active internal bleeding",
      "status": "likely_not_met",
      "confidence_score": 95,
      "evidence_from_vignette": "There is no mention of trauma, fractures, or bleeding in the clinical information."
    }
  ]
}
```

## Step 4: Final Recommendation

### Prompt Sent to LLM:
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

{
  "extracted_clinical_entities": {
    "symptoms": [
      "high fever (39.5°C)",
      "increased work of breathing",
      "decreased oral intake"
    ],
    "medical_problems": [
      "history of prematurity at 32 weeks",
      "previous RSV bronchiolitis at 6 months requiring PICU admission and brief HFNC support",
      "respiratory distress"
    ],
    "medications": [
      "albuterol nebulizers",
      "ipratropium nebulizers"
    ],
    "vital_signs": {
      "heart rate": "145",
      "respiratory rate": "35",
      "blood pressure": "90/60",
      "oxygen saturation": "93% on room air (RA)"
    },
    "demographics": {
      "age": "3 years",
      "weight": null,
      "sex": "male"
    },
    "medical_history": "History of prematurity at 32 weeks, previous RSV bronchiolitis at 6 months requiring PICU admission and brief HFNC support.",
    "clinical_context": "Currently on albuterol and ipratropium nebs with minimal improvement. Symptoms present for the past 2 days."
  },
  "identified_specialties_needed": [
    {
      "specialty_name": "Pulmonology",
      "likelihood_score": 95,
      "supporting_evidence": "Patient presents with respiratory distress (RR 35), increased work of breathing, and decreased oxygen saturation (93% on RA). History includes prematurity and previous RSV bronchiolitis, suggesting underlying respiratory vulnerability. Current presentation requires expert management of respiratory failure."
    },
    {
      "specialty_name": "Neonatology",
      "likelihood_score": 70,
      "supporting_evidence": "Patient has a history of prematurity at 32 weeks, which often leads to long-term respiratory issues. Previous severe RSV bronchiolitis requiring PICU admission and HFNC support indicates a history of significant respiratory illness common in premature infants. Neonatology expertise may be valuable given this background."
    },
    {
      "specialty_name": "Infectious Disease",
      "likelihood_score": 60,
      "supporting_evidence": "Patient presents with respiratory distress and fever (39.5°C), raising concern for a respiratory infection (e.g., pneumonia, severe viral illness). History of prematurity increases susceptibility to infections. Infectious disease consultation may be needed to identify the pathogen and guide antimicrobial therapy."
    },
    {
      "specialty_name": "Cardiology",
      "likelihood_score": 20,
      "supporting_evidence": "Patient has tachycardia (HR 145) and respiratory distress. While primarily respiratory, cardiac involvement cannot be entirely excluded in severe illness. Cardiology consultation is less likely but may be considered if cardiac dysfunction is suspected or if there are specific cardiac findings."
    }
  ],
  "exclusion_criteria_evaluation": [
    {
      "exclusion_rule_id": "1",
      "rule_text": "Patients requiring active cardiopulmonary resuscitation",
      "status": "likely_not_met",
      "confidence_score": 95,
      "evidence_from_vignette": "The patient has vital signs documented (HR 145, RR 35, BP 90/60, SpO2 93%) and is described as receiving nebulizer treatments. There is no mention of cardiac arrest or CPR being performed, suggesting the patient has a pulse and spontaneous circulation."
    },
    {
      "exclusion_rule_id": "2",
      "rule_text": "Patients with unstable airway or requiring intubation during transport",
      "status": "likely_not_met",
      "confidence_score": 85,
      "evidence_from_vignette": "While the patient has increased work of breathing, they are maintaining an oxygen saturation of 93% on room air and are receiving nebulizer treatments (albuterol and ipratropium). There is no mention of impending respiratory failure, stridor, or need for intubation."
    },
    {
      "exclusion_rule_id": "3",
      "rule_text": "Patients with severe respiratory distress or SpO2 <90% on maximal supplemental oxygen",
      "status": "likely_not_met",
      "confidence_score": 80,
      "evidence_from_vignette": "The patient has increased work of breathing but maintains SpO2 of 93% on room air (not requiring supplemental oxygen). While the patient has tachypnea (RR 35) indicating respiratory distress, they are not described as having severe distress and are maintaining adequate oxygenation without supplemental oxygen."
    }
  ]
}

Determine the most appropriate care level for this patient. Consider the clinical entities, specialty needs, and exclusion criteria evaluations.
Provide a confidence score (0-100) for your recommendation and explain your reasoning in detail.
```

### LLM Response:
```json
{
  "recommended_care_level": "PICU",
  "confidence": 95,
  "explanation": "Patient presents with significant respiratory distress (RR 35), increased work of breathing, and decreased oxygen saturation (93% on RA). History includes prematurity at 32 weeks and previous severe RSV bronchiolitis requiring PICU admission and HFNC support, indicating a history of significant respiratory illness and potential underlying vulnerability. Current presentation requires intensive monitoring and management of potential respiratory failure, likely including supplemental oxygen, possible non-invasive ventilation, and close observation. Pulmonology expertise is highly indicated given the respiratory distress and history. PICU admission allows for this level of care and specialist involvement."
}
```

## Final Analysis Result

The complete analysis of the clinical vignette resulted in:

```json
{
  "chief_complaint": "history of prematurity at 32 weeks",
  "clinical_history": "History of prematurity at 32 weeks, previous RSV bronchiolitis at 6 months requiring PICU admission and brief HFNC support.",
  "vital_signs": {
    "heart rate": "145",
    "respiratory rate": "35",
    "blood pressure": "90/60",
    "oxygen saturation": "93% on room air (RA)"
  },
  "age": "3 years",
  "weight_kg": null,
  "sex": "male",
  "keywords": [
    "high fever (39.5°C)",
    "increased work of breathing",
    "decreased oral intake",
    "history of prematurity at 32 weeks",
    "previous RSV bronchiolitis at 6 months requiring PICU admission and brief HFNC support",
    "respiratory distress"
  ],
  "suggested_care_level": "PICU",
  "note": "Generated by medgemma-27b-text-it using multi-step prompting",
  "specialty_needs": [
    {
      "specialty_name": "Pulmonology",
      "likelihood_score": 95,
      "supporting_evidence": "Patient presents with respiratory distress (RR 35), increased work of breathing, and decreased oxygen saturation (93% on RA). History includes prematurity and previous RSV bronchiolitis, suggesting underlying respiratory vulnerability. Current presentation requires expert management of respiratory failure."
    },
    {
      "specialty_name": "Neonatology",
      "likelihood_score": 70,
      "supporting_evidence": "Patient has a history of prematurity at 32 weeks, which often leads to long-term respiratory issues. Previous severe RSV bronchiolitis requiring PICU admission and HFNC support indicates a history of significant respiratory illness common in premature infants. Neonatology expertise may be valuable given this background."
    },
    {
      "specialty_name": "Infectious Disease",
      "likelihood_score": 60,
      "supporting_evidence": "Patient presents with respiratory distress and fever (39.5°C), raising concern for a respiratory infection (e.g., pneumonia, severe viral illness). History of prematurity increases susceptibility to infections. Infectious disease consultation may be needed to identify the pathogen and guide antimicrobial therapy."
    },
    {
      "specialty_name": "Cardiology",
      "likelihood_score": 20,
      "supporting_evidence": "Patient has tachycardia (HR 145) and respiratory distress. While primarily respiratory, cardiac involvement cannot be entirely excluded in severe illness. Cardiology consultation is less likely but may be considered if cardiac dysfunction is suspected or if there are specific cardiac findings."
    }
  ],
  "exclusion_matches": [],
  "explainability": {
    "reasoning": "Patient presents with significant respiratory distress (RR 35), increased work of breathing, and decreased oxygen saturation (93% on RA). History includes prematurity at 32 weeks and previous severe RSV bronchiolitis requiring PICU admission and HFNC support, indicating a history of significant respiratory illness and potential underlying vulnerability. Current presentation requires intensive monitoring and management of potential respiratory failure, likely including supplemental oxygen, possible non-invasive ventilation, and close observation. Pulmonology expertise is highly indicated given the respiratory distress and history. PICU admission allows for this level of care and specialist involvement.",
    "confidence": 95
  }
}
```
