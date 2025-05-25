#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for recommendation processing without GUI

This script tests the processing of LLM recommendations, including handling
of markdown-formatted JSON responses, without requiring the GUI.
"""

import json
import logging
from src.llm.robust_recommendation_handler import RecommendationHandler
from src.core.models import Recommendation, LLMReasoningDetails

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_recommendation_from_direct_json():
    """Test processing a recommendation from direct JSON"""
    logger.info("=== Testing recommendation from direct JSON ===")
    
    # Sample JSON that would come from an LLM
    sample_json = {
        "recommended_campus_id": "TCH_MAIN_TMC",
        "recommended_campus_name": "Texas Children's Hospital - Main Campus (MC)",
        "care_level": "PICU",
        "confidence_score": 85,
        "explainability_details": {
            "main_recommendation_reason": "The Main Campus has PICU capabilities",
            "alternative_reasons": {
                "TCH_WOODLANDS": "Lacks required specialists"
            },
            "key_factors_considered": ["distance", "specialty_match"],
            "confidence_explanation": "High confidence based on clear specialty match"
        }
    }
    
    # Create test request
    request_id = "TEST-123"
    
    # Test direct JSON processing
    recommendation = RecommendationHandler.extract_recommendation(
        {"recommendation_data": sample_json}, request_id
    )
    
    # Display results
    print(f"Recommendation campus: {recommendation.recommended_campus_id}")
    print(f"Confidence score: {recommendation.confidence_score}")
    print(f"Care level: {recommendation.recommended_level_of_care}")
    
    # Check explainability details
    if hasattr(recommendation, 'explainability_details'):
        details = recommendation.explainability_details
        print("\nExplainability details:")
        if hasattr(details, 'main_recommendation_reason'):
            print(f"Main reason: {details.main_recommendation_reason}")
        if hasattr(details, 'key_factors_considered'):
            print(f"Factors considered: {details.key_factors_considered}")
        if hasattr(details, 'alternative_reasons'):
            print(f"Alternative reasons: {details.alternative_reasons}")
    
    return recommendation

def test_recommendation_from_markdown_json():
    """Test processing a recommendation from markdown-wrapped JSON"""
    logger.info("=== Testing recommendation from markdown-wrapped JSON ===")
    
    # Sample JSON wrapped in markdown code blocks as LLM might return
    markdown_json = """```json
{
  "recommended_campus_id": "TCH_MAIN_TMC",
  "recommended_campus_name": "Texas Children's Hospital - Main Campus (MC)",
  "care_level": "PICU",
  "confidence_score": 85,
  "explainability_details": {
    "main_recommendation_reason": "The Main Campus has PICU capabilities",
    "alternative_reasons": {
      "TCH_WOODLANDS": "Lacks required specialists"
    },
    "key_factors_considered": ["distance", "specialty_match"],
    "confidence_explanation": "High confidence based on clear specialty match"
  },
  "notes": ["Patient requires immediate PICU care"],
  "transport_details": {
    "mode": "GROUND_AMBULANCE",
    "estimated_time_minutes": 30,
    "special_requirements": "Critical care transport team"
  },
  "conditions": {
    "weather": "Clear, 75F",
    "traffic": "Light traffic"
  }
}
```"""

    # Create test request with the output field as LLM would return
    request_id = "TEST-456"
    
    # Test markdown JSON processing - this is what we fixed in the handler
    recommendation = RecommendationHandler.extract_recommendation(
        {"output": markdown_json}, request_id
    )
    
    # Display results
    print(f"Recommendation campus: {recommendation.recommended_campus_id}")
    print(f"Confidence score: {recommendation.confidence_score}")
    print(f"Care level: {recommendation.recommended_level_of_care}")
    
    # Check explainability details
    if hasattr(recommendation, 'explainability_details'):
        details = recommendation.explainability_details
        print("\nExplainability details:")
        if hasattr(details, 'main_recommendation_reason'):
            print(f"Main reason: {details.main_recommendation_reason}")
        if hasattr(details, 'key_factors_considered'):
            print(f"Factors considered: {details.key_factors_considered}")
        if hasattr(details, 'alternative_reasons'):
            print(f"Alternative reasons: {details.alternative_reasons}")
    
    return recommendation

def test_pediatric_scoring():
    """Test the pediatric scoring systems"""
    logger.info("=== Testing pediatric scoring systems ===")
    
    from src.core.scoring.pediatric import (
        calculate_pews,
        calculate_trap,
        calculate_cameo2,
    )
    
    # Sample patient data
    patient_data = {
        "age_months": 36,
        "vital_signs": {
            "heart_rate": 140,
            "respiratory_rate": 35,
            "oxygen_saturation": 92,
            "temperature": 38.5,
            "capillary_refill": 2.5
        },
        "respiratory_effort": "moderate",
        "oxygen_requirement": "low",
        "behavior": "irritable"
    }
    
    # Test PEWS
    pews_result = calculate_pews(
        age_months=patient_data["age_months"],
        respiratory_rate=patient_data["vital_signs"]["respiratory_rate"],
        respiratory_effort=patient_data["respiratory_effort"],
        oxygen_requirement=patient_data["oxygen_requirement"],
        heart_rate=patient_data["vital_signs"]["heart_rate"],
        capillary_refill=patient_data["vital_signs"]["capillary_refill"],
        behavior=patient_data["behavior"]
    )
    
    print("\nPEWS Result:")
    print(f"Total score: {pews_result['total_score']}")
    print(f"Interpretation: {pews_result['interpretation']}")
    print(f"Recommended action: {pews_result['recommended_action']}")
    
    # Test TRAP
    trap_result = calculate_trap(
        respiratory_status="moderate distress",
        hemodynamic_status="stable with intervention",
        neurologic_status="irritable",
        access_difficulty="moderate"
    )
    
    print("\nTRAP Result:")
    print(f"Risk level: {trap_result['risk_level']}")
    print(f"Recommended team: {trap_result['recommended_team']}")
    
    # Test CAMEO II
    cameo_result = calculate_cameo2(
        physiologic_instability=3,
        intervention_complexity=2,
        nursing_dependency=2
    )
    
    print("\nCAMEO II Result:")
    print(f"Total score: {cameo_result['total_score']}")
    print(f"Acuity level: {cameo_result['acuity_level']}")
    print(f"Recommended ratio: {cameo_result['recommended_ratio']}")
    
    return {
        "pews": pews_result,
        "trap": trap_result,
        "cameo2": cameo_result
    }

if __name__ == "__main__":
    print("\n=== TRANSFER CENTER FUNCTIONALITY TEST ===\n")
    
    # Test JSON extraction and recommendation processing
    direct_rec = test_recommendation_from_direct_json()
    
    print("\n" + "="*50 + "\n")
    
    # Test markdown JSON extraction (our fix)
    markdown_rec = test_recommendation_from_markdown_json()
    
    print("\n" + "="*50 + "\n")
    
    # Test pediatric scoring systems
    scoring_results = test_pediatric_scoring()
    
    print("\n" + "="*50 + "\n")
    print("Tests completed!")
