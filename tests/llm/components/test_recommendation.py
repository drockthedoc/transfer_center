#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for LLM Recommendation Component

This module tests the recommendation generation functionality which synthesizes
patient data, severity scores, and hospital capabilities to produce transfer recommendations.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.llm.components.recommendation import (
    generate_transfer_recommendation,
    prioritize_care_requirements,
    format_recommendation,
)


class TestRecommendationComponent(unittest.TestCase):
    """Test cases for the recommendation component"""

    def test_prioritize_care_requirements(self):
        """Test prioritization of care requirements based on severity scores"""
        # Test high severity pediatric case
        patient_data = {
            "patient_demographics": {
                "age_years": 3,
                "weight_kg": 14,
            },
            "vital_signs": {
                "heart_rate": "150",
                "respiratory_rate": "40",
                "oxygen_saturation": "88",
                "temperature": "39.2C",
            },
            "severity_scores": {
                "pews": {"score": 8, "interpretation": "High Risk"},
                "trap": {"score": 9, "interpretation": "High Risk"},
                "chews": {"score": 7, "interpretation": "Critical Alert"}
            },
            "condition": "Respiratory distress, suspected pneumonia"
        }
        
        priorities = prioritize_care_requirements(patient_data)
        
        self.assertEqual(priorities["level_of_care"], "critical")
        self.assertIn("pediatric_icu", priorities["required_services"])
        self.assertIn("pediatric_pulmonology", priorities["specialist_needs"])
        self.assertTrue(priorities["time_sensitive"])
        
        # Test moderate severity case
        moderate_data = {
            "patient_demographics": {
                "age_years": 10,
                "weight_kg": 35,
            },
            "vital_signs": {
                "heart_rate": "110",
                "respiratory_rate": "24",
                "oxygen_saturation": "94",
                "temperature": "38.0C",
            },
            "severity_scores": {
                "pews": {"score": 4, "interpretation": "Medium Risk"},
                "trap": {"score": 5, "interpretation": "Medium Risk"},
                "chews": {"score": 3, "interpretation": "Yellow Alert"}
            },
            "condition": "Uncomplicated appendicitis"
        }
        
        moderate_priorities = prioritize_care_requirements(moderate_data)
        
        self.assertEqual(moderate_priorities["level_of_care"], "intermediate")
        self.assertIn("pediatric_surgery", moderate_priorities["required_services"])
        self.assertFalse(moderate_priorities["time_sensitive"])

    @patch('src.llm.components.recommendation.prioritize_care_requirements')
    def test_generate_transfer_recommendation(self, mock_prioritize):
        """Test generation of transfer recommendations"""
        # Setup mock
        mock_prioritize.return_value = {
            "level_of_care": "critical",
            "required_services": ["pediatric_icu", "pediatric_pulmonology"],
            "specialist_needs": ["pediatric_pulmonologist", "critical_care"],
            "time_sensitive": True
        }
        
        # Test data
        patient_data = {
            "patient_demographics": {"age_years": 3},
            "vital_signs": {"respiratory_rate": "40"},
            "severity_scores": {
                "pews": {"score": 8},
                "trap": {"score": 9}
            },
            "condition": "Respiratory distress"
        }
        
        hospitals = [
            {
                "name": "Children's Medical Center",
                "distance_miles": 15,
                "available_services": ["pediatric_icu", "pediatric_pulmonology", "pediatric_emergency"],
                "capabilities": {"level_of_care": "critical", "pediatric_specific": True},
                "census": {"icu_beds_available": 3}
            },
            {
                "name": "Community Hospital",
                "distance_miles": 5,
                "available_services": ["emergency", "general_pediatrics"],
                "capabilities": {"level_of_care": "intermediate", "pediatric_specific": False},
                "census": {"icu_beds_available": 2}
            }
        ]
        
        transport_options = {
            "ground_ambulance": {"available": True, "estimated_time_minutes": 25},
            "helicopter": {"available": True, "estimated_time_minutes": 10}
        }
        
        # Call function
        result = generate_transfer_recommendation(patient_data, hospitals, transport_options)
        
        # Verify results
        self.assertEqual(result["recommended_hospital"], "Children's Medical Center")
        self.assertEqual(result["recommended_transport"], "helicopter")
        self.assertIn("recommendation_factors", result)
        self.assertIn("severity_assessment", result)
        self.assertIn("alternative_options", result)
        
        # Verify mock was called
        mock_prioritize.assert_called_once_with(patient_data)
        
        # Test with limited hospital options
        limited_hospitals = [
            {
                "name": "Community Hospital",
                "distance_miles": 5,
                "available_services": ["emergency", "general_pediatrics"],
                "capabilities": {"level_of_care": "intermediate", "pediatric_specific": False},
                "census": {"icu_beds_available": 0}
            }
        ]
        
        limited_result = generate_transfer_recommendation(patient_data, limited_hospitals, transport_options)
        
        self.assertEqual(limited_result["recommended_hospital"], "Community Hospital")
        self.assertIn("warning", limited_result)
        self.assertIn("capability_gaps", limited_result)

    def test_format_recommendation(self):
        """Test formatting of recommendation for display"""
        # Test data
        recommendation = {
            "recommended_hospital": "Children's Medical Center",
            "recommended_transport": "helicopter",
            "recommendation_factors": [
                "Patient requires pediatric ICU care",
                "Time-sensitive condition requires rapid transport",
                "Specialized pediatric pulmonology services needed"
            ],
            "severity_assessment": {
                "pews_score": 8,
                "trap_score": 9,
                "overall_severity": "critical"
            },
            "transport_time_estimates": {
                "ground_minutes": 25,
                "air_minutes": 10
            }
        }
        
        patient_info = {
            "age_years": 3,
            "condition": "Respiratory distress, suspected pneumonia",
            "vital_signs": {
                "heart_rate": "150",
                "respiratory_rate": "40",
                "oxygen_saturation": "88"
            }
        }
        
        # Call function
        formatted = format_recommendation(recommendation, patient_info)
        
        # Verify results
        self.assertIn("RECOMMENDED HOSPITAL", formatted)
        self.assertIn("Children's Medical Center", formatted)
        self.assertIn("TRANSPORT RECOMMENDATION", formatted)
        self.assertIn("helicopter", formatted)
        self.assertIn("SEVERITY ASSESSMENT", formatted)
        self.assertIn("critical", formatted)
        self.assertIn("PATIENT INFORMATION", formatted)
        self.assertIn("RECOMMENDATION FACTORS", formatted)


if __name__ == "__main__":
    unittest.main()
