#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for LLM Exclusion Evaluation Component

This module tests the exclusion evaluation functionality which determines
if a patient meets exclusion criteria for transfer.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.llm.components.exclusion_evaluation import (
    evaluate_exclusion_criteria,
    check_patient_against_criteria,
    format_exclusion_results,
)


class TestExclusionEvaluation(unittest.TestCase):
    """Test cases for the exclusion evaluation component"""

    def test_check_patient_against_criteria(self):
        """Test checking patient data against exclusion criteria"""
        # Test with matching exclusion criteria
        patient_data = {
            "age_years": 2,
            "weight_kg": 12,
            "vital_signs": {
                "heart_rate": "150",
                "respiratory_rate": "35",
                "oxygen_saturation": "92",
                "temperature": "38.5C"
            },
            "diagnosis": "Bronchiolitis",
            "clinical_notes": "Moderate respiratory distress, responding to treatment"
        }
        
        exclusion_criteria = [
            {
                "condition": "bronchiolitis",
                "criteria": [
                    {"type": "age", "description": "Age < 1 year", "value": "< 1 year"},
                    {"type": "oxygen", "description": "Requiring > 2L O2", "value": "> 2L O2"},
                    {"type": "respiratory", "description": "Severe respiratory distress", "value": "severe distress"}
                ]
            },
            {
                "condition": "simple_fracture",
                "criteria": [
                    {"type": "age", "description": "Age < 18 years", "value": "< 18 years"},
                    {"type": "neurovascular", "description": "Neurovascularly intact", "value": "intact"}
                ]
            }
        ]
        
        result = check_patient_against_criteria(patient_data, exclusion_criteria)
        
        # Patient should match bronchiolitis condition but not all criteria
        self.assertTrue(result["matched_conditions"]["bronchiolitis"]["condition_match"])
        self.assertFalse(result["matched_conditions"]["bronchiolitis"]["meets_all_criteria"])
        self.assertNotIn("simple_fracture", result["matched_conditions"])
        
        # Test with fully matching criteria
        young_patient = {
            "age_years": 0.5,  # 6 months
            "weight_kg": 7,
            "vital_signs": {
                "heart_rate": "160",
                "respiratory_rate": "45",
                "oxygen_saturation": "88",
                "oxygen_requirement": "3L NC",
                "temperature": "38.7C"
            },
            "diagnosis": "Severe Bronchiolitis",
            "clinical_notes": "Severe respiratory distress, requiring oxygen"
        }
        
        young_result = check_patient_against_criteria(young_patient, exclusion_criteria)
        
        # Patient should match bronchiolitis and meet all criteria
        self.assertTrue(young_result["matched_conditions"]["bronchiolitis"]["condition_match"])
        self.assertTrue(young_result["matched_conditions"]["bronchiolitis"]["meets_all_criteria"])

    @patch('src.llm.components.exclusion_evaluation.llm_client')
    def test_evaluate_exclusion_criteria_with_llm(self, mock_llm):
        """Test evaluation of exclusion criteria using LLM"""
        # Mock LLM response
        mock_llm.evaluate_exclusion.return_value = {
            "exclusion_determination": True,
            "matched_criteria": [
                "Age < 1 year (Patient is 6 months)",
                "Requiring > 2L O2 (Patient on 3L NC)",
                "Severe respiratory distress (Confirmed in notes)"
            ],
            "recommended_action": "Manage at local facility",
            "rationale": "Patient meets all exclusion criteria for bronchiolitis"
        }
        
        # Test data
        patient_data = {
            "age_years": 0.5,
            "diagnosis": "Bronchiolitis",
            "vital_signs": {
                "oxygen_requirement": "3L NC"
            },
            "clinical_notes": "Severe respiratory distress"
        }
        
        exclusion_criteria = [
            {
                "condition": "bronchiolitis",
                "criteria": [
                    {"type": "age", "description": "Age < 1 year", "value": "< 1 year"},
                    {"type": "oxygen", "description": "Requiring > 2L O2", "value": "> 2L O2"},
                    {"type": "respiratory", "description": "Severe respiratory distress", "value": "severe distress"}
                ]
            }
        ]
        
        # Call function
        result = evaluate_exclusion_criteria(patient_data, exclusion_criteria, use_llm=True)
        
        # Verify results
        self.assertTrue(result["meets_exclusion_criteria"])
        self.assertIn("matched_criteria", result)
        self.assertIn("recommended_action", result)
        self.assertEqual(len(result["matched_criteria"]), 3)
        
        # Verify LLM was called
        mock_llm.evaluate_exclusion.assert_called_once()

    def test_evaluate_exclusion_criteria_without_llm(self):
        """Test evaluation of exclusion criteria without using LLM"""
        # Test data
        patient_data = {
            "age_years": 10,
            "weight_kg": 35,
            "vital_signs": {
                "heart_rate": "90",
                "respiratory_rate": "18",
                "oxygen_saturation": "99",
                "temperature": "37.0C"
            },
            "diagnosis": "Simple forearm fracture",
            "clinical_notes": "Closed, non-displaced fracture. Neurovascularly intact."
        }
        
        exclusion_criteria = [
            {
                "condition": "simple_fracture",
                "criteria": [
                    {"type": "age", "description": "Age < 18 years", "value": "< 18 years"},
                    {"type": "neurovascular", "description": "Neurovascularly intact", "value": "intact"}
                ]
            }
        ]
        
        # Call function
        result = evaluate_exclusion_criteria(patient_data, exclusion_criteria, use_llm=False)
        
        # Verify results
        self.assertTrue(result["meets_exclusion_criteria"])
        self.assertIn("matched_criteria", result)
        self.assertEqual(len(result["matched_criteria"]), 2)

    def test_format_exclusion_results(self):
        """Test formatting of exclusion evaluation results"""
        # Test with exclusion criteria met
        exclusion_results = {
            "meets_exclusion_criteria": True,
            "matched_criteria": [
                "Age < 1 year (Patient is 6 months)",
                "Requiring > 2L O2 (Patient on 3L NC)",
                "Severe respiratory distress (Confirmed in notes)"
            ],
            "recommended_action": "Manage at local facility",
            "rationale": "Patient meets all exclusion criteria for bronchiolitis",
            "condition": "bronchiolitis"
        }
        
        formatted = format_exclusion_results(exclusion_results)
        
        # Verify formatting
        self.assertIn("EXCLUSION CRITERIA MET", formatted)
        self.assertIn("bronchiolitis", formatted)
        self.assertIn("Manage at local facility", formatted)
        self.assertIn("Age < 1 year", formatted)
        
        # Test with exclusion criteria not met
        non_exclusion = {
            "meets_exclusion_criteria": False,
            "matched_criteria": [],
            "recommended_action": "Consider transfer",
            "rationale": "Patient does not meet any exclusion criteria",
            "condition": None
        }
        
        non_formatted = format_exclusion_results(non_exclusion)
        
        # Verify formatting
        self.assertIn("NO EXCLUSION CRITERIA MET", non_formatted)
        self.assertIn("Consider transfer", non_formatted)


if __name__ == "__main__":
    unittest.main()
