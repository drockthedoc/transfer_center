#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for Robust Recommendation Handler

This module tests the robust recommendation handling functionality, 
particularly the extraction of JSON from LLM responses including those
wrapped in markdown code blocks.
"""

import unittest
import json
from unittest.mock import patch, MagicMock

from src.core.models import Recommendation, LLMReasoningDetails
from src.llm.robust_recommendation_handler import RecommendationHandler

class TestRobustRecommendationHandler(unittest.TestCase):
    """Test case for the robust recommendation handler"""
    
    def setUp(self):
        """Set up test data for all tests"""
        # Sample JSON data that might be returned by an LLM
        self.sample_json = {
            "recommended_campus_id": "CAMPUS_A",
            "recommended_campus_name": "Main Campus",
            "care_level": "PICU",
            "confidence_score": 85,
            "explainability_details": {
                "main_recommendation_reason": "This is the main campus with PICU capabilities",
                "alternative_reasons": {
                    "CAMPUS_B": "Lacks required specialists",
                    "CAMPUS_C": "Too far from patient location"
                },
                "key_factors_considered": ["distance", "specialty_match", "bed_availability"],
                "confidence_explanation": "High confidence based on clear specialty match"
            },
            "notes": ["Patient requires PICU care", "Notify specialty team on arrival"],
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
        
        # Same JSON wrapped in markdown code blocks as LLM might return
        self.markdown_json = f"""```json
{json.dumps(self.sample_json, indent=2)}
```"""

        # JSON with different format markdown
        self.markdown_json_alt = f"""Here's my recommendation:

```
{json.dumps(self.sample_json, indent=2)}
```

Hope this helps!"""

        # Sample LLM extraction with output field containing markdown
        self.llm_extraction_output = {
            "output": self.markdown_json
        }
        
        # Sample request ID for testing
        self.request_id = "TEST-123"
    
    def test_extract_json_from_markdown(self):
        """Test extracting JSON from markdown code blocks"""
        # Define a local function to access the local extract_json_if_needed function
        # This is needed because it's defined inside extract_recommendation
        def extract_from_markdown(text):
            # Helper function to extract JSON from markdown code blocks if needed
            if isinstance(text, str) and '```' in text:
                try:
                    import re
                    # Extract content between triple backticks
                    pattern = r'```(?:json)?\\n([\\s\\S]*?)\\n```'
                    match = re.search(pattern, text)
                    if match:
                        json_content = match.group(1).strip()
                        return json.loads(json_content)
                except Exception:
                    pass
            return text
            
        # Test direct JSON extraction
        result = extract_from_markdown(self.markdown_json)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["recommended_campus_id"], "CAMPUS_A")
        
        # Test alternative markdown format
        result = extract_from_markdown(self.markdown_json_alt)
        self.assertIsInstance(result, str)  # Should remain string as pattern doesn't match
    
    def test_extract_recommendation_from_markdown(self):
        """Test extracting recommendation from markdown-wrapped JSON"""
        # Extract recommendation from output field with markdown
        recommendation = RecommendationHandler.extract_recommendation(
            self.llm_extraction_output, self.request_id
        )
        
        # Verify the extracted recommendation
        self.assertIsInstance(recommendation, Recommendation)
        self.assertEqual(recommendation.recommended_campus_id, "CAMPUS_A")
        self.assertEqual(recommendation.confidence_score, 85)
        
        # Check that explainability details were correctly processed
        self.assertIsInstance(recommendation.explainability_details, LLMReasoningDetails)
        self.assertEqual(
            recommendation.explainability_details.main_recommendation_reason,
            "This is the main campus with PICU capabilities"
        )
        self.assertEqual(len(recommendation.explainability_details.key_factors_considered), 3)
    
    def test_extract_recommendation_from_direct_json(self):
        """Test extracting recommendation from direct JSON data"""
        # Extract recommendation from direct JSON
        recommendation = RecommendationHandler.extract_recommendation(
            {"recommendation_data": self.sample_json}, self.request_id
        )
        
        # Verify the extracted recommendation
        self.assertIsInstance(recommendation, Recommendation)
        self.assertEqual(recommendation.recommended_campus_id, "CAMPUS_A")
        
        # Check explainability details
        self.assertIsInstance(recommendation.explainability_details, LLMReasoningDetails)
        self.assertEqual(
            recommendation.explainability_details.main_recommendation_reason,
            "This is the main campus with PICU capabilities"
        )
    
    def test_extract_recommendation_with_missing_data(self):
        """Test extracting recommendation with missing data"""
        # Test with minimal valid data
        minimal_data = {
            "recommended_campus_id": "CAMPUS_A",
            "reason": "Test reason"
        }
        
        recommendation = RecommendationHandler.extract_recommendation(
            {"recommendation_data": minimal_data}, self.request_id
        )
        
        # Verify fallbacks work for missing fields
        self.assertEqual(recommendation.recommended_campus_id, "CAMPUS_A")
        self.assertEqual(recommendation.reason, "Test reason")
        self.assertIsNotNone(recommendation.explainability_details)
    
    def test_create_error_recommendation(self):
        """Test creating an error recommendation"""
        error_message = "Test error message"
        
        # Create error recommendation
        recommendation = RecommendationHandler.create_error_recommendation(
            self.request_id, error_message
        )
        
        # Verify error recommendation
        self.assertEqual(recommendation.recommended_campus_id, "ERROR")
        self.assertEqual(recommendation.reason, error_message)
        self.assertLess(recommendation.confidence_score, 20)  # Should be low confidence


if __name__ == '__main__':
    unittest.main()
