#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for Score Processor Module

This module tests the score processor functionality which combines multiple
pediatric severity scoring systems to generate a comprehensive assessment.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.core.scoring.score_processor import (
    process_all_scores,
    generate_score_summary,
    determine_severity_level,
)


class TestScoreProcessor(unittest.TestCase):
    """Test cases for the score processor functionality"""

    @patch('src.core.scoring.score_processor.calculate_pews')
    @patch('src.core.scoring.score_processor.calculate_trap')
    @patch('src.core.scoring.score_processor.calculate_cameo2')
    @patch('src.core.scoring.score_processor.calculate_prism3')
    def test_process_all_scores(self, mock_prism, mock_cameo, mock_trap, mock_pews):
        """Test processing of all pediatric severity scores"""
        # Mock score calculations - ensuring they match the actual detailed structure
        mock_pews.return_value = {
            "score": 7, "interpretation": "High Risk", "action": "Immediate PICU transfer",
            "subscores": {"respiratory": 3, "cardiovascular": 2, "behavior": 2},
            "normal_ranges": {"heart_rate": "100-180", "respiratory_rate": "30-60"}
        }
        
        mock_trap.return_value = {
            "score": 8, "risk_level": "High Risk", "transport_recommendation": "Critical Care Team",
            "subscores": {"respiratory": 3, "hemodynamic": 2, "neurologic": 2, "access": 1}
        }
        
        # For CAMEO and PRISM, we can keep the existing mocks as they are not the focus of this subtask
        mock_cameo.return_value = {
            "score": 12, "acuity_level": "High", "staffing_recommendation": "1:1", # Matched key from implementation
            "subscores": {"physiologic_instability": 5, "respiratory_support": 4, "nursing_dependency": 3} # Example subscore keys
        }
        
        mock_prism.return_value = {
            "score": 9, "interpretation": "Medium Risk", # Matched key from implementation
            "subscores": {"cardiovascular": 3, "neurological": 2, "acid_base": 2, "chemistry": 1, "hematologic":1 } # Example subscore keys
        }
        
        # Test data - simplified as extract_vital_signs will be mocked or tested separately
        # The key is that calculate_all_scores correctly passes through what it gets.
        patient_data = {
            "age_months": 36,
            "vital_signs": {
                "heart_rate": 150,
                "respiratory_rate": 40,
                "oxygen_saturation": 88,
                "temperature": 39.2,
                "blood_pressure": "90/50",
                "capillary_refill": 3,
            },
            "respiratory_effort": "increased",
            "oxygen_requirement": "high_flow",
            "behavior": "lethargic",
            "labs": {
                "wbc": 15000,
                "hemoglobin": 10.5,
                "platelets": 180000,
                "sodium": 145,
                "potassium": 3.8,
                "calcium": 8.5,
                "glucose": 110,
                "creatinine": 0.5
            }
        }
        
        # Call function
        result = process_all_scores(patient_data)
        
        # Verify results
        self.assertIn("pews", result)
        self.assertIn("trap", result)
        self.assertIn("cameo2", result)
        self.assertIn("prism3", result)
        
        self.assertEqual(result["pews"]["score"], 7)
        self.assertEqual(result["trap"]["score"], 8)
        self.assertEqual(result["cameo2"]["score"], 12)
        self.assertEqual(result["prism3"]["score"], 9)
        
        # Verify mocks were called with appropriate data
        mock_pews.assert_called_once()
        mock_trap.assert_called_once()
        mock_cameo.assert_called_once()
        mock_prism.assert_called_once()
        
        # Test with missing data
        limited_data = {
            "age_months": 36,
            "vital_signs": {
                "heart_rate": 150,
                "respiratory_rate": 40
            }
        }
        
        # Reset mocks
        mock_pews.reset_mock()
        mock_trap.reset_mock()
        mock_cameo.reset_mock()
        mock_prism.reset_mock()
        
        # Set up PEWS to return valid score but others to indicate missing data
        # Ensure the mocked PEWS return matches its actual detailed structure
        mock_pews.return_value = {
            "score": 5, "interpretation": "Medium Risk", "action": "Frequent monitoring",
            "subscores": {"respiratory": 2, "cardiovascular": 2, "behavior": 1},
            "normal_ranges": {"heart_rate": "100-180", "respiratory_rate": "30-60"}
        }
        
        # Ensure the mocked TRAP return matches its actual detailed structure
        mock_trap.return_value = {
            "score": "N/A", "risk_level": "N/A", "transport_recommendation": "N/A",
            "missing_parameters": ["hemodynamic_status", "neurologic_status"],
            "subscores": {"respiratory": "N/A", "hemodynamic": "N/A", "neurologic": "N/A", "access": "N/A"}
        }
        
        mock_cameo.return_value = { # CAMEO and PRISM mocks can remain simpler if not focus
            "score": "N/A", "acuity_level": "N/A", "staffing_recommendation": "N/A",
            "missing_parameters": ["interventions", "nursing_dependency"]
        }
        
        mock_prism.return_value = { # CAMEO and PRISM mocks can remain simpler if not focus
            "score": "N/A", "interpretation": "N/A",
            "missing_parameters": ["labs", "blood_pressure"]
        }
        
        # Call function with limited data
        limited_result = process_all_scores(limited_data)
        
        # Should have PEWS score but others marked as incomplete
        self.assertEqual(limited_result["pews"]["score"], 5)
        self.assertEqual(limited_result["trap"]["score"], "N/A")
        self.assertEqual(limited_result["cameo2"]["score"], "N/A")
        self.assertEqual(limited_result["prism3"]["score"], "N/A")
        
        # All mocks should still be called
        mock_pews.assert_called_once()
        mock_trap.assert_called_once()
        mock_cameo.assert_called_once()
        mock_prism.assert_called_once()

    def test_generate_score_summary(self):
        """Test generation of summary from multiple scores"""
        # Test data
        scores = {
            "pews": {
                "score": 7,
                "interpretation": "High Risk",
                "action": "Immediate PICU transfer"
            },
            "trap": {
                "score": 8,
                "risk_level": "High Risk",
                "transport_recommendation": "Critical Care Team"
            },
            "cameo2": {
                "score": 12,
                "acuity_level": "High",
                "nurse_ratio": "1:1"
            },
            "prism3": {
                "score": 9,
                "mortality_risk": "Medium"
            }
        }
        
        # Call function
        summary = generate_score_summary(scores)
        
        # Verify results
        self.assertIn("overall_severity", summary)
        self.assertEqual(summary["overall_severity"], "high")
        self.assertIn("recommended_care_level", summary)
        self.assertEqual(summary["recommended_care_level"], "picu")
        self.assertIn("transport_recommendation", summary)
        self.assertEqual(summary["transport_recommendation"], "Critical Care Team")
        self.assertIn("score_concordance", summary)
        self.assertTrue(summary["score_concordance"] > 0.8)  # High concordance
        
        # Test with mixed severity
        mixed_scores = {
            "pews": {
                "score": 5,
                "interpretation": "Medium Risk",
                "action": "Frequent monitoring"
            },
            "trap": {
                "score": 6,
                "risk_level": "Medium Risk",
                "transport_recommendation": "ALS Team"
            },
            "cameo2": {
                "score": 8,
                "acuity_level": "Medium",
                "nurse_ratio": "1:2"
            },
            "prism3": {
                "score": 4,
                "mortality_risk": "Low"
            }
        }
        
        mixed_summary = generate_score_summary(mixed_scores)
        self.assertEqual(mixed_summary["overall_severity"], "medium")
        
        # Test with incomplete data
        incomplete_scores = {
            "pews": {
                "score": 7,
                "interpretation": "High Risk"
            },
            "trap": {
                "score": "N/A",
                "missing_parameters": ["hemodynamic_status"]
            },
            "cameo2": {
                "score": "N/A",
                "missing_parameters": ["interventions"]
            },
            "prism3": {
                "score": "N/A",
                "missing_parameters": ["labs"]
            }
        }
        
        incomplete_summary = generate_score_summary(incomplete_scores)
        self.assertEqual(incomplete_summary["overall_severity"], "high")  # Based on PEWS only
        self.assertIn("data_completeness", incomplete_summary)
        self.assertLess(incomplete_summary["data_completeness"], 50)  # Low completeness
        self.assertIn("confidence", incomplete_summary)
        self.assertLess(incomplete_summary["confidence"], 70)  # Lower confidence

    def test_determine_severity_level(self):
        """Test determination of severity level from multiple scores"""
        # Test high severity
        high_scores = {
            "pews": {"score": 8},
            "trap": {"score": 9},
            "cameo2": {"score": 14},
            "prism3": {"score": 12}
        }
        
        self.assertEqual(determine_severity_level(high_scores), "high")
        
        # Test medium severity
        medium_scores = {
            "pews": {"score": 4},
            "trap": {"score": 5},
            "cameo2": {"score": 8},
            "prism3": {"score": 6}
        }
        
        self.assertEqual(determine_severity_level(medium_scores), "medium")
        
        # Test low severity
        low_scores = {
            "pews": {"score": 2},
            "trap": {"score": 3},
            "cameo2": {"score": 4},
            "prism3": {"score": 2}
        }
        
        self.assertEqual(determine_severity_level(low_scores), "low")
        
        # Test mixed severity (should weigh PEWS and TRAP more heavily)
        mixed_scores = {
            "pews": {"score": 7},  # High
            "trap": {"score": 6},  # Medium-high
            "cameo2": {"score": 5},  # Medium
            "prism3": {"score": 3}   # Low
        }
        
        self.assertEqual(determine_severity_level(mixed_scores), "high")
        
        # Test with missing scores
        partial_scores = {
            "pews": {"score": 6},  # Medium-high
            "trap": {"score": "N/A"},
            "cameo2": {"score": "N/A"},
            "prism3": {"score": "N/A"}
        }
        
        self.assertEqual(determine_severity_level(partial_scores), "medium-high")


if __name__ == "__main__":
    unittest.main()
