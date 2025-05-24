#!/usr/bin/env python
"""
Test script for recommendation handling without GUI interaction.
This tests the LLM functionality and recommendation extraction directly.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('recommendation_test')

# Import necessary components
try:
    from src.llm.llm_classifier_refactored import LLMClassifier
    from src.llm.robust_recommendation_handler import RecommendationHandler
    from src.core.models import TransferRequest, Location, PatientData, TransportMode, Recommendation
except ImportError as e:
    logger.error(f"Error importing required modules: {e}")
    logger.error("Make sure you're running this from the project root directory")
    sys.exit(1)

def create_test_request(clinical_text: str, facility_name: str) -> TransferRequest:
    """Create a test transfer request with the given clinical text and facility."""
    # Sample coordinates for testing
    # Darnall Army Medical Center coordinates
    facility_coordinates = {
        "darnall army medical center": (31.0768, -97.7673)
    }
    
    # Get coordinates or use defaults
    lat, lon = facility_coordinates.get(
        facility_name.lower(), 
        facility_coordinates["darnall army medical center"]  # Default
    )
    
    # Create patient data
    patient = PatientData(
        patient_id=f"TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        clinical_text=clinical_text,
        extracted_data={},
        care_needs=[],
        care_level="General"  # Default, will be determined by processing
    )
    
    # Create transfer request
    request = TransferRequest(
        request_id=f"REQ_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        patient_data=patient,
        clinical_notes=clinical_text,
        sending_location=Location(
            latitude=lat,
            longitude=lon,
        ),
        requested_datetime=datetime.now(),
        transport_mode=TransportMode.GROUND_AMBULANCE,
        transport_info={
            "type": "ALS",
            "mode": "Ground",
            "departure_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    
    return request

def generate_pediatric_scores(clinical_text: str) -> Dict[str, Any]:
    """Generate mock pediatric scores for testing."""
    # This is a simplified version - in production, you'd use actual scoring systems
    
    # Extract key information for scoring
    import re
    
    # Mock scores dictionary
    scores = {}
    
    # Try to extract vital signs for scoring
    hr_match = re.search(r"HR\s+(\d+)", clinical_text)
    rr_match = re.search(r"RR\s+(\d+)", clinical_text)
    spo2_match = re.search(r"SpO2\s+(\d+)%", clinical_text)
    
    hr = int(hr_match.group(1)) if hr_match else 120
    rr = int(rr_match.group(1)) if rr_match else 20
    spo2 = int(spo2_match.group(1)) if spo2_match else 98
    
    # Generate PEWS score
    pews_score = 0
    # HR scoring
    if hr > 140:
        pews_score += 2
    elif hr > 120:
        pews_score += 1
    
    # RR scoring
    if rr > 30:
        pews_score += 2
    elif rr > 20:
        pews_score += 1
    
    # SpO2 scoring
    if spo2 < 92:
        pews_score += 2
    elif spo2 < 95:
        pews_score += 1
    
    # Work of breathing - look for indicators in text
    if "increased work of breathing" in clinical_text.lower():
        pews_score += 2
    
    # Add the PEWS score
    scores["pews"] = {
        "total_score": pews_score,
        "recommendation": "Monitor closely" if pews_score < 5 else "Consider PICU" if pews_score < 7 else "PICU transfer recommended"
    }
    
    # Generate TRAP score (Transport Risk Assessment in Pediatrics)
    trap_score = 0
    
    # Respiratory component
    if "breathing" in clinical_text.lower() and any(x in clinical_text.lower() for x in ["difficulty", "distress", "increased work"]):
        trap_score += 2
    
    # Oxygenation component
    if spo2 < 94:
        trap_score += 2
    elif spo2 < 97:
        trap_score += 1
    
    # Previous PICU history
    if "picu" in clinical_text.lower():
        trap_score += 1
    
    # Set risk level based on score
    risk_level = "Low"
    if trap_score >= 4:
        risk_level = "High"
    elif trap_score >= 2:
        risk_level = "Medium"
    
    # Add the TRAP score
    scores["trap"] = {
        "total_score": trap_score,
        "risk_level": risk_level,
        "recommendation": f"{risk_level} risk during transport. " + 
                         ("Consider specialized team." if risk_level != "Low" else "Standard transport team recommended.")
    }
    
    # Return all scores in the expected format
    return {"scores": scores}

def process_recommendation(clinical_text: str, facility_name: str, api_url: Optional[str] = None) -> None:
    """Process a recommendation using the provided clinical text and facility."""
    logger.info("Starting recommendation test")
    logger.info(f"Clinical text: {clinical_text[:100]}...")
    logger.info(f"Facility: {facility_name}")
    
    # Create test request
    request = create_test_request(clinical_text, facility_name)
    logger.info(f"Created test request with ID: {request.request_id}")
    
    # Generate pediatric scores
    scoring_results = generate_pediatric_scores(clinical_text)
    logger.info(f"Generated pediatric scores: {list(scoring_results['scores'].keys())}")
    
    try:
        # Initialize LLM classifier
        llm_classifier = LLMClassifier()
        # Set the specified model
        llm_classifier.set_model("medgemma-27b-text-it")
        
        if api_url:
            llm_classifier.set_api_url(api_url)
            
        logger.info(f"Using LLM model: medgemma-27b-text-it")
        
        logger.info("Processing text with LLM classifier")
        
        # Try processing with LLM
        try:
            extracted_data = llm_classifier.process_text(
                clinical_text, 
                human_suggestions=None, 
                scoring_results=scoring_results
            )
            
            if not extracted_data:
                logger.error("LLM returned empty data")
                raise ValueError("Empty data returned from LLM")
                
            # Use the robust handler to extract the recommendation
            recommendation = RecommendationHandler.extract_recommendation(
                extracted_data=extracted_data,
                request_id=request.request_id
            )
            
            # Display the recommendation
            logger.info("===== RECOMMENDATION DETAILS =====")
            logger.info(f"Recommended Campus: {recommendation.recommended_campus_id}")
            logger.info(f"Confidence Score: {recommendation.confidence_score}%")
            logger.info(f"Reason: {recommendation.reason}")
            
            if recommendation.notes:
                logger.info("Notes:")
                for note in recommendation.notes:
                    logger.info(f"  - {note}")
            
            # Display explainability details if available
            if recommendation.explainability_details:
                logger.info("Explainability Details:")
                print(json.dumps(recommendation.explainability_details, indent=2))
            
        except Exception as llm_error:
            logger.error(f"LLM processing error: {llm_error}")
            logger.info("Falling back to rule-based recommendation")
            
            # Generate rule-based recommendation as fallback
            recommendation = RecommendationHandler.extract_rule_based_recommendation(
                clinical_text=clinical_text,
                request_id=request.request_id,
                scoring_results=scoring_results
            )
            
            # Display the rule-based recommendation
            logger.info("===== RULE-BASED RECOMMENDATION DETAILS =====")
            logger.info(f"Recommended Campus: {recommendation.recommended_campus_id}")
            logger.info(f"Confidence Score: {recommendation.confidence_score}%")
            logger.info(f"Reason: {recommendation.reason}")
            
            if recommendation.notes:
                logger.info("Notes:")
                for note in recommendation.notes:
                    logger.info(f"  - {note}")
    
    except Exception as e:
        logger.error(f"Critical error in recommendation process: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # Clinical vignette
    clinical_text = """3-year-old male presenting with high fever (39.5°C), increased work of breathing, and decreased oral intake for the past 2 days. HR 145, RR 35, BP 90/60, SpO2 93% on RA. History of prematurity at 32 weeks, previous RSV bronchiolitis at 6 months requiring PICU admission and brief HFNC support. Currently on albuterol and ipratropium nebs with minimal improvement."""
    
    # Facility
    facility = "Darnall Army Medical Center"
    
    # Optional: LLM API URL (if needed)
    api_url = None  # Set this if you need to override the default
    
    # Process the recommendation
    process_recommendation(clinical_text, facility, api_url)
