#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for Transport Evaluation Module

This module tests the transport evaluation functionality which assesses
different transport options and makes recommendations based on patient data.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.core.decision.transport_evaluation import (
    evaluate_transport_options,
    calculate_transport_urgency,
    determine_appropriate_transport_mode,
)


class TestTransportEvaluation(unittest.TestCase):
    """Test cases for the transport evaluation functions"""

    def test_calculate_transport_urgency(self):
        """Test calculation of transport urgency based on patient data"""
        # Critical patient
        critical_data = {
            "vital_signs": {
                "heart_rate": 180,
                "respiratory_rate": 45,
                "blood_pressure": "70/40",
                "oxygen_saturation": 82,
            },
            "chief_complaint": "Respiratory distress",
            "age_years": 3,
        }
        
        critical_urgency = calculate_transport_urgency(critical_data)
        self.assertEqual(critical_urgency, "critical")
        
        # Urgent patient
        urgent_data = {
            "vital_signs": {
                "heart_rate": 150,
                "respiratory_rate": 30,
                "blood_pressure": "85/55",
                "oxygen_saturation": 92,
            },
            "chief_complaint": "Febrile seizure",
            "age_years": 2,
        }
        
        urgent_urgency = calculate_transport_urgency(urgent_data)
        self.assertEqual(urgent_urgency, "urgent")
        
        # Non-urgent patient
        non_urgent_data = {
            "vital_signs": {
                "heart_rate": 110,
                "respiratory_rate": 22,
                "blood_pressure": "100/70",
                "oxygen_saturation": 98,
            },
            "chief_complaint": "Simple fracture",
            "age_years": 10,
        }
        
        non_urgent_urgency = calculate_transport_urgency(non_urgent_data)
        self.assertEqual(non_urgent_urgency, "non-urgent")

    def test_determine_appropriate_transport_mode(self):
        """Test determination of appropriate transport mode"""
        # Test for ground ambulance
        ground_mode = determine_appropriate_transport_mode(
            distance_miles=20,
            urgency="urgent",
            weather_conditions="clear",
            traffic_conditions="light",
            available_resources=["ground_ambulance", "helicopter"],
            patient_stability="stable"
        )
        self.assertEqual(ground_mode, "ground_ambulance")
        
        # Test for helicopter
        air_mode = determine_appropriate_transport_mode(
            distance_miles=120,
            urgency="critical",
            weather_conditions="clear",
            traffic_conditions="heavy",
            available_resources=["ground_ambulance", "helicopter"],
            patient_stability="unstable"
        )
        self.assertEqual(air_mode, "helicopter")
        
        # Test when helicopter is preferred but weather prohibits
        weather_constraint = determine_appropriate_transport_mode(
            distance_miles=120,
            urgency="critical",
            weather_conditions="severe_thunderstorm",
            traffic_conditions="heavy",
            available_resources=["ground_ambulance", "helicopter"],
            patient_stability="unstable"
        )
        self.assertEqual(weather_constraint, "ground_ambulance")
        
        # Test when first choice not available
        limited_resources = determine_appropriate_transport_mode(
            distance_miles=120,
            urgency="critical",
            weather_conditions="clear",
            traffic_conditions="heavy",
            available_resources=["ground_ambulance"],  # No helicopter
            patient_stability="unstable"
        )
        self.assertEqual(limited_resources, "ground_ambulance")

    @patch('src.core.decision.transport_evaluation.calculate_transport_urgency')
    @patch('src.core.decision.transport_evaluation.determine_appropriate_transport_mode')
    def test_evaluate_transport_options(self, mock_mode, mock_urgency):
        """Test the main evaluate_transport_options function"""
        # Setup mocks
        mock_urgency.return_value = "urgent"
        mock_mode.return_value = "helicopter"
        
        # Test data
        patient_data = {
            "vital_signs": {
                "heart_rate": 150,
                "respiratory_rate": 30,
            },
            "age_years": 5,
        }
        
        transport_conditions = {
            "distance_miles": 80,
            "weather_conditions": "clear",
            "traffic_conditions": "moderate",
            "available_resources": ["ground_ambulance", "helicopter"],
        }
        
        # Call function
        result = evaluate_transport_options(patient_data, transport_conditions)
        
        # Verify results
        self.assertEqual(result["recommended_mode"], "helicopter")
        self.assertEqual(result["urgency"], "urgent")
        self.assertIn("estimated_transport_time", result)
        self.assertIn("care_recommendations", result)
        
        # Verify mocks were called correctly
        mock_urgency.assert_called_once_with(patient_data)
        mock_mode.assert_called_once_with(
            distance_miles=80,
            urgency="urgent",
            weather_conditions="clear",
            traffic_conditions="moderate",
            available_resources=["ground_ambulance", "helicopter"],
            patient_stability=unittest.mock.ANY  # Don't strictly check this derived value
        )


if __name__ == "__main__":
    unittest.main()
