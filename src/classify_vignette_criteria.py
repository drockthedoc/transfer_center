#!/usr/bin/env python3

import os
import sys
import yaml
import json
from openai import OpenAI

# Ensure the project root is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Configuration ---
EXCLUSION_CRITERIA_YAML_PATH = os.path.join(project_root, 'data', 'exclusion_criteria.yaml')
OUTPUT_FILE_PATH = os.path.join(project_root, 'vignette_classifications.json')

# LLM Configuration
LLM_BASE_URL = "http://localhost:1234/v1" # Standard for LM Studio OpenAI-compatible server
LLM_MODEL_NAME = "biomistral-merged-zephyr"
# API key is often not required for local OpenAI-compatible servers
# If your server requires one, set it here or via an environment variable
LLM_API_KEY = "not-needed"

# Sample Vignette (can be replaced by command-line arg later)
PATIENT_VIGNETTE = """
8 yo male without significant PMH presents with a left humerus fracture.
Fell off a rockwall onto side.
Seen at UC and transferred to OSH.
XR shows a proximal humerus fracture, mild displacement.
NV intact, no penetrating skin trauma.
No other injuries sustained.
Splinted for comfort.
Recommendations: Typically managed conservatively with coaptation splint and outpatient follow up.
Please discuss with family that no other interventions may be necessary after our eval.
Vitals: 103/63, HR 111, RR 22, SpO2 99%.
Coming ground EMS from Houston Methodist Cypress.
"""

def load_all_criteria_from_yaml(file_path: str) -> list:
    """Loads all individual criteria items from the YAML file."""
    all_criteria_items = []
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        if not data:
            print(f"Warning: YAML file {file_path} is empty or could not be parsed correctly.")
            return []

        for campus_name, campus_data in data.items():
            if not isinstance(campus_data, dict):
                continue # Skip non-campus sections like 'community_sites_general_info'
            
            for category_key, category_content in campus_data.items():
                if isinstance(category_content, dict) and 'criteria' in category_content and isinstance(category_content['criteria'], list):
                    for criterion_dict in category_content['criteria']:
                        if isinstance(criterion_dict, dict):
                            # Add some context to the criterion for clarity
                            criterion_dict['_campus_name'] = campus_name
                            criterion_dict['_category_key'] = category_key
                            all_criteria_items.append(criterion_dict)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return []
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {file_path}: {e}")
        return []
    return all_criteria_items

def classify_criterion_with_llm(client: OpenAI, vignette: str, criterion: dict) -> dict:
    """Uses the LLM to classify if the vignette meets a single criterion."""
    criterion_text = criterion.get('condition', 'No condition text found')
    search_keywords = criterion.get('search_keywords', [])
    full_criterion_context = f"{criterion_text}"
    if search_keywords and isinstance(search_keywords, list):
        full_criterion_context += f" (Keywords: {', '.join(search_keywords)})"

    prompt = f"""Patient Vignette:
{vignette}

Exclusion Criterion:
{full_criterion_context}

Does this specific exclusion criterion apply to the patient described in the vignette?
Respond with a JSON object containing two keys: "applies" (boolean: true or false) and "reason" (string: a brief explanation for your decision).
Example Response: {{"applies": false, "reason": "The patient's age is outside the specified range for this criterion."}}
"""

    try:
        completion = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful clinical assistant performing exclusion criteria checks. Respond only with the requested JSON object."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2, # Lower temperature for more deterministic classification
        )
        response_content = completion.choices[0].message.content
        # Attempt to parse the JSON response
        try:
            classification_result = json.loads(response_content)
            if not isinstance(classification_result, dict) or 'applies' not in classification_result or 'reason' not in classification_result:
                 # Fallback if JSON is not as expected
                return {"applies": None, "reason": f"LLM response not in expected JSON format: {response_content}", "error": True}
            return classification_result
        except json.JSONDecodeError:
            return {"applies": None, "reason": f"Failed to parse LLM JSON response: {response_content}", "error": True}

    except Exception as e:
        print(f"Error during LLM call for criterion '{criterion_text[:50]}...': {e}")
        return {"applies": None, "reason": str(e), "error": True}

def main():
    print(f"Starting vignette classification against criteria from {EXCLUSION_CRITERIA_YAML_PATH}")
    print(f"Using LLM: {LLM_MODEL_NAME} at {LLM_BASE_URL}")
    print(f"Output will be saved to: {OUTPUT_FILE_PATH}\n")

    # Initialize OpenAI client for local server
    client = OpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
    )

    all_criteria = load_all_criteria_from_yaml(EXCLUSION_CRITERIA_YAML_PATH)
    if not all_criteria:
        print("No exclusion criteria loaded. Exiting.")
        return

    print(f"Loaded {len(all_criteria)} individual criteria to process.")

    classification_results = []

    for i, criterion in enumerate(all_criteria):
        print(f"Processing criterion {i+1}/{len(all_criteria)}: {criterion.get('condition', 'N/A')[:70]}...")
        
        llm_response = classify_criterion_with_llm(client, PATIENT_VIGNETTE, criterion)
        
        result_entry = {
            "criterion_campus": criterion.get('_campus_name'),
            "criterion_category": criterion.get('_category_key'),
            "criterion_condition": criterion.get('condition'),
            "criterion_disposition": criterion.get('disposition'),
            "criterion_keywords": criterion.get('search_keywords'),
            "llm_classification": llm_response.get('applies'),
            "llm_reason": llm_response.get('reason')
        }
        if llm_response.get('error'):
            result_entry['llm_error'] = True
        
        classification_results.append(result_entry)

    # Save results to JSON file
    try:
        with open(OUTPUT_FILE_PATH, 'w') as f:
            json.dump(classification_results, f, indent=2)
        print(f"\nSuccessfully wrote {len(classification_results)} classification results to {OUTPUT_FILE_PATH}")
    except IOError as e:
        print(f"\nError writing results to file: {e}")

if __name__ == '__main__':
    main()
