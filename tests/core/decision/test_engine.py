#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for Decision Engine Module

This module tests the decision engine functionality which is the core
component for making transfer recommendations.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.core.decision.engine import (
    generate_recommendation,
    evaluate_hospital_suitability,
    select_optimal_destination,
)


class TestDecisionEngine(unittest.TestCase):
    """Test cases for the decision engine functions"""

    def test_evaluate_hospital_suitability(self):
        """Test evaluation of hospital suitability for a patient"""
        # Hospital with all needed capabilities
        patient_needs = {
            "required_services": ["pediatric_icu", "trauma_level_2", "neurosurgery"],
            "preferred_services": ["pediatric_cardiology"],
            "level_of_care": "critical"
        }
        
        good_hospital = {
            "name": "Children's Medical Center",
            "available_services": ["pediatric_icu", "trauma_level_1", "neurosurgery", 
                                   "pediatric_cardiology", "pediatric_emergency"],
            "census": {"icu_beds_available": 5, "total_beds_available": 20},
            "capabilities": {"pediatric_specific": True, "level_of_care": "critical"}
        }
        
        suitability = evaluate_hospital_suitability(patient_needs, good_hospital)
        self.assertGreaterEqual(suitability["score"], 90)
        self.assertEqual(suitability["match_level"], "excellent")
        
        # Hospital missing critical services
        limited_hospital = {
            "name": "Community Hospital",
            "available_services": ["emergency", "general_surgery"],
            "census": {"icu_beds_available": 2, "total_beds_available": 30},
            "capabilities": {"pediatric_specific": False, "level_of_care": "moderate"}
        }
        
        limited_suitability = evaluate_hospital_suitability(patient_needs, limited_hospital)
        self.assertLess(limited_suitability["score"], 50)
        self.assertIn(limited_suitability["match_level"], ["poor", "inadequate"])
        
        # Hospital with no ICU beds
        no_beds_hospital = {
            "name": "Children's Medical Center",
            "available_services": ["pediatric_icu", "trauma_level_1", "neurosurgery", 
                                   "pediatric_cardiology", "pediatric_emergency"],
            "census": {"icu_beds_available": 0, "total_beds_available": 5},
            "capabilities": {"pediatric_specific": True, "level_of_care": "critical"}
        }
        
        no_beds_suitability = evaluate_hospital_suitability(patient_needs, no_beds_hospital)
        self.assertLess(no_beds_suitability["score"], 90)  # Should be penalized
        self.assertIn("No ICU beds available", no_beds_suitability["issues"])

    def test_select_optimal_destination(self):
        """Test selection of optimal destination from multiple options"""
        patient_needs = {
            "required_services": ["pediatric_emergency", "orthopedics"],
            "level_of_care": "moderate"
        }
        
        hospitals = [
            {
                "name": "Children's Hospital",
                "suitability": {"score": 95, "match_level": "excellent"},
                "distance_miles": 30,
                "estimated_travel_time_minutes": 45
            },
            {
                "name": "University Medical Center",
                "suitability": {"score": 90, "match_level": "excellent"},
                "distance_miles": 15,
                "estimated_travel_time_minutes": 25
            },
            {
                "name": "Community Hospital",
                "suitability": {"score": 70, "match_level": "good"},
                "distance_miles": 10,
                "estimated_travel_time_minutes": 15
            }
        ]
        
        # Test standard case - balanced scoring
        result = select_optimal_destination(patient_needs, hospitals)
        self.assertEqual(result["recommended_hospital"], "University Medical Center")
        
        # Test critical case - prioritize capability over distance
        critical_needs = {
            "required_services": ["pediatric_icu", "trauma_level_1"],
            "level_of_care": "critical"
        }
        
        critical_result = select_optimal_destination(critical_needs, hospitals)
        self.assertEqual(critical_result["recommended_hospital"], "Children's Hospital")
        
        # Test stable case - prioritize proximity
        stable_needs = {
            "required_services": ["pediatric_emergency"],
            "level_of_care": "minimal"
        }
        
        stable_result = select_optimal_destination(stable_needs, hospitals)
        self.assertEqual(stable_result["recommended_hospital"], "Community Hospital")

    @patch('src.core.decision.engine.evaluate_hospital_suitability')
    @patch('src.core.decision.engine.select_optimal_destination')
    def test_generate_recommendation(self, mock_select, mock_evaluate):
        """Test the main generate_recommendation function"""
        # Setup mocks
        mock_evaluate.return_value = {"score": 95, "match_level": "excellent"}
        mock_select.return_value = {
            "recommended_hospital": "Children's Hospital",
            "recommendation_factors": ["Best overall match", "Specialized in pediatrics"]
        }
        
        # Test data
        patient_data = {
            "age_years": 5,
            "chief_complaint": "Respiratory distress",
            "vital_signs": {"heart_rate": 140, "respiratory_rate": 32},
            "severity_scores": {"pews": 7, "trap": 8},
        }
        
        hospitals = [
            {"name": "Children's Hospital", "available_services": ["pediatric_icu"]},
            {"name": "Community Hospital", "available_services": ["emergency"]}
        ]
        
        # Call function
        result = generate_recommendation(patient_data, hospitals)
        
        # Verify results
        self.assertEqual(result["recommended_hospital"], "Children's Hospital")
        self.assertIn("recommendation_factors", result)
        self.assertIn("alternative_options", result)
        self.assertIn("severity_assessment", result)
        
        # Verify mocks were called correctly
        mock_evaluate.assert_called()
        mock_select.assert_called_once()


if __name__ == "__main__":
    unittest.main()
