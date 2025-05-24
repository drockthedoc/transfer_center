#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for LLM Specialty Assessment Component

This module tests the specialty assessment functionality which determines
the appropriate specialties needed for a patient based on their condition.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.llm.components.specialty_assessment import (
    assess_required_specialties,
    determine_specialty_urgency,
    match_specialists_to_hospitals,
)


class TestSpecialtyAssessment(unittest.TestCase):
    """Test cases for the specialty assessment component"""

    @patch('src.llm.components.specialty_assessment.llm_client')
    def test_assess_required_specialties(self, mock_llm):
        """Test assessment of required specialties for a patient"""
        # Mock LLM response
        mock_llm.identify_specialties.return_value = {
            "primary_specialty": "pediatric_neurology",
            "secondary_specialties": ["pediatric_critical_care", "neurosurgery"],
            "rationale": "Patient presents with seizures and altered mental status"
        }
        
        # Test data
        patient_data = {
            "age_years": 7,
            "condition": "Status epilepticus, altered mental status",
            "vital_signs": {
                "heart_rate": "130",
                "respiratory_rate": "22",
                "oxygen_saturation": "95"
            },
            "clinical_notes": "Patient with history of epilepsy, now with prolonged seizure activity"
        }
        
        # Call function
        result = assess_required_specialties(patient_data)
        
        # Verify results
        self.assertEqual(result["primary_specialty"], "pediatric_neurology")
        self.assertIn("pediatric_critical_care", result["secondary_specialties"])
        self.assertIn("neurosurgery", result["secondary_specialties"])
        self.assertIn("rationale", result)
        
        # Verify LLM was called
        mock_llm.identify_specialties.assert_called_once()

    def test_determine_specialty_urgency(self):
        """Test determination of specialty consultation urgency"""
        # Test critical case
        critical_specialties = {
            "primary_specialty": "pediatric_critical_care",
            "secondary_specialties": ["pediatric_pulmonology", "infectious_disease"],
            "rationale": "Severe respiratory distress, possible sepsis"
        }
        
        critical_vitals = {
            "heart_rate": "160",
            "respiratory_rate": "45",
            "oxygen_saturation": "85",
            "blood_pressure": "80/40"
        }
        
        critical_urgency = determine_specialty_urgency(critical_specialties, critical_vitals)
        self.assertEqual(critical_urgency["primary_urgency"], "immediate")
        self.assertEqual(critical_urgency["secondary_urgencies"]["pediatric_pulmonology"], "urgent")
        
        # Test urgent but not critical case
        urgent_specialties = {
            "primary_specialty": "pediatric_surgery",
            "secondary_specialties": ["pediatric_anesthesiology"],
            "rationale": "Appendicitis with signs of perforation"
        }
        
        urgent_vitals = {
            "heart_rate": "120",
            "respiratory_rate": "24",
            "oxygen_saturation": "97",
            "blood_pressure": "100/70"
        }
        
        urgent_urgency = determine_specialty_urgency(urgent_specialties, urgent_vitals)
        self.assertEqual(urgent_urgency["primary_urgency"], "urgent")
        
        # Test routine case
        routine_specialties = {
            "primary_specialty": "pediatric_orthopedics",
            "secondary_specialties": [],
            "rationale": "Simple forearm fracture, neurovascularly intact"
        }
        
        routine_vitals = {
            "heart_rate": "95",
            "respiratory_rate": "18",
            "oxygen_saturation": "99",
            "blood_pressure": "110/70"
        }
        
        routine_urgency = determine_specialty_urgency(routine_specialties, routine_vitals)
        self.assertEqual(routine_urgency["primary_urgency"], "routine")

    def test_match_specialists_to_hospitals(self):
        """Test matching of required specialties to available hospitals"""
        # Test data
        required_specialties = {
            "primary_specialty": "pediatric_neurosurgery",
            "secondary_specialties": ["pediatric_critical_care", "neurology"],
            "urgency": {
                "primary_urgency": "immediate",
                "secondary_urgencies": {
                    "pediatric_critical_care": "immediate", 
                    "neurology": "urgent"
                }
            }
        }
        
        hospitals = [
            {
                "name": "Children's Medical Center",
                "available_services": [
                    "pediatric_neurosurgery", 
                    "pediatric_critical_care", 
                    "neurology", 
                    "pediatric_emergency"
                ],
                "specialist_availability": {
                    "pediatric_neurosurgery": "24/7",
                    "pediatric_critical_care": "24/7",
                    "neurology": "on-call"
                },
                "distance_miles": 25
            },
            {
                "name": "University Hospital",
                "available_services": [
                    "neurosurgery",  # Adult, not pediatric
                    "critical_care", 
                    "neurology", 
                    "emergency"
                ],
                "specialist_availability": {
                    "neurosurgery": "24/7",
                    "critical_care": "24/7",
                    "neurology": "24/7"
                },
                "distance_miles": 10
            },
            {
                "name": "Community Hospital",
                "available_services": [
                    "emergency",
                    "general_surgery"
                ],
                "specialist_availability": {},
                "distance_miles": 5
            }
        ]
        
        # Call function
        result = match_specialists_to_hospitals(required_specialties, hospitals)
        
        # Verify results
        self.assertEqual(result["best_match"]["name"], "Children's Medical Center")
        self.assertEqual(len(result["best_match"]["matching_specialties"]), 3)
        self.assertEqual(result["alternative_matches"][0]["name"], "University Hospital")
        self.assertGreater(
            result["best_match"]["specialty_match_score"],
            result["alternative_matches"][0]["specialty_match_score"]
        )
        
        # The closest hospital should be ranked lowest due to lack of specialties
        self.assertEqual(result["alternative_matches"][-1]["name"], "Community Hospital")


if __name__ == "__main__":
    unittest.main()
