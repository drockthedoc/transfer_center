#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for Confidence Estimator Module

This module tests the confidence estimation functionality which evaluates
the reliability of recommendations based on data completeness and quality.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.core.decision.confidence_estimator import (
    estimate_confidence,
    calculate_data_completeness,
    evaluate_recommendation_confidence,
)


class TestConfidenceEstimator(unittest.TestCase):
    """Test cases for the confidence estimator functions"""

    def test_calculate_data_completeness(self):
        """Test calculation of data completeness percentage"""
        # Test with complete data
        complete_data = {
            "patient_age": 5,
            "patient_weight": 20,
            "heart_rate": 100,
            "respiratory_rate": 22,
            "blood_pressure": "90/60",
            "oxygen_saturation": 98,
            "chief_complaint": "Fever",
        }
        
        completeness = calculate_data_completeness(complete_data)
        self.assertGreaterEqual(completeness, 90)  # Should be high completeness
        
        # Test with partially complete data
        partial_data = {
            "patient_age": 5,
            "heart_rate": None,
            "respiratory_rate": 22,
            "blood_pressure": None,
            "chief_complaint": "Fever",
        }
        
        completeness = calculate_data_completeness(partial_data)
        self.assertLess(completeness, 90)  # Should be lower completeness
        self.assertGreaterEqual(completeness, 40)  # But still have some data
        
        # Test with minimal data
        minimal_data = {
            "patient_age": 5,
            "chief_complaint": "Fever",
        }
        
        completeness = calculate_data_completeness(minimal_data)
        self.assertLess(completeness, 40)  # Should be low completeness

    def test_evaluate_recommendation_confidence(self):
        """Test evaluation of recommendation confidence"""
        # Test high confidence scenario
        high_confidence = evaluate_recommendation_confidence(
            data_completeness=95,
            recommendation_strength=85,
            has_consistent_indicators=True
        )
        self.assertGreaterEqual(high_confidence, 80)
        
        # Test medium confidence scenario
        medium_confidence = evaluate_recommendation_confidence(
            data_completeness=70,
            recommendation_strength=60,
            has_consistent_indicators=True
        )
        self.assertGreaterEqual(medium_confidence, 50)
        self.assertLess(medium_confidence, 80)
        
        # Test low confidence scenario
        low_confidence = evaluate_recommendation_confidence(
            data_completeness=40,
            recommendation_strength=50,
            has_consistent_indicators=False
        )
        self.assertLess(low_confidence, 50)

    @patch('src.core.decision.confidence_estimator.calculate_data_completeness')
    @patch('src.core.decision.confidence_estimator.evaluate_recommendation_confidence')
    def test_estimate_confidence(self, mock_evaluate, mock_completeness):
        """Test the main estimate_confidence function"""
        # Setup mocks
        mock_completeness.return_value = 80
        mock_evaluate.return_value = 75
        
        # Test data and recommendation
        patient_data = {
            "patient_age": 5,
            "heart_rate": 100,
            "respiratory_rate": 22,
        }
        
        recommendation = {
            "strength": 70,
            "consistent_indicators": True
        }
        
        # Call function
        result = estimate_confidence(patient_data, recommendation)
        
        # Verify results
        self.assertEqual(result["confidence_score"], 75)
        self.assertIn("data_completeness", result)
        self.assertIn("factors", result)
        
        # Verify mocks were called correctly
        mock_completeness.assert_called_once_with(patient_data)
        mock_evaluate.assert_called_once_with(
            data_completeness=80,
            recommendation_strength=70,
            has_consistent_indicators=True
        )


if __name__ == "__main__":
    unittest.main()
