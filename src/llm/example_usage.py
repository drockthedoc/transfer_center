"""
Example Usage of LLM Prompt Chaining

This script demonstrates how to use the LLM prompt chaining system
for analyzing patient vignettes and making transfer recommendations.
"""

import json
import logging
from src.llm.interface import llm_interface
from src.core.models import HospitalCampus

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def example_analyze_patient():
    """
    Example function demonstrating the use of the LLM interface.
    """
    # Sample patient vignette
    patient_vignette = """
    10-year-old male presented with fever (39.2°C), cough, and difficulty breathing for 3 days.
    History of asthma. Vital signs: HR 110, BP 100/70, RR 28, O2 sat 91% on room air.
    Physical exam reveals wheezing and decreased breath sounds in the right lower lobe.
    Recently diagnosed with pneumonia by chest x-ray at outside facility.
    Weight is 35 kg. No neurological symptoms reported.
    """
    
    # Sample target campuses
    target_campuses = [
        HospitalCampus(
            id="austin",
            name="Austin Campus",
            latitude=30.2672,
            longitude=-97.7431,
            address="123 Medical Dr, Austin, TX 78701"
        ),
        HospitalCampus(
            id="community",
            name="Community Campus",
            latitude=30.3472,
            longitude=-97.8231,
            address="456 Healthcare Ave, Austin, TX 78731"
        )
    ]
    
    # Analyze the patient for transfer
    results = llm_interface.analyze_patient_for_transfer(patient_vignette, target_campuses)
    
    # Print the results
    print("\n========== PATIENT ANALYSIS RESULTS ==========\n")
    
    print("EXTRACTED PATIENT DATA:")
    print(f"Age: {results['extracted_patient_data']['age']}")
    print(f"Weight: {results['extracted_patient_data']['weight_kg']} kg")
    print(f"Chief Complaint: {results['extracted_patient_data']['chief_complaint']}")
    print(f"Extraction Source: {results['extracted_patient_data']['extraction_source']}")
    
    print("\nCAMPUS ANALYSES:")
    for analysis in results['campus_analyses']:
        print(f"\n{analysis['campus_name']}:")
        print(f"  Suitable: {'Yes' if analysis['is_suitable'] else 'No'}")
        
        if analysis['exclusions']:
            print("  Exclusions:")
            for excl in analysis['exclusions']:
                print(f"    - {excl['name']}: {excl['description']}")
        
        if analysis['specialty_needs']:
            print("  Specialty Needs:")
            for spec in analysis['specialty_needs']:
                print(f"    - {spec['name']} (Likelihood: {spec['likelihood']}%)")
        
        print(f"  Recommended Care Level: {analysis['recommended_care_level']}")
        print(f"  Confidence: {analysis['confidence']}%")
    
    print("\nFINAL RECOMMENDATION:")
    print(f"Recommended Campus: {results['recommended_campus']['name']}")
    print(f"Recommended Care Level: {results['recommended_care_level']}")
    print(f"Explanation: {results['explanation']}")

if __name__ == "__main__":
    example_analyze_patient()
