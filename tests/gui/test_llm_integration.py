#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for LLM Integration in GUI

This module tests the LLM integration in the GUI, including the robust fallback
mechanisms and error handling for vital signs extraction.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.gui.llm_integration import (
    extract_patient_data_with_fallback,
    process_llm_extraction,
    determine_care_level,
)


class TestLLMIntegration(unittest.TestCase):
    """Test cases for LLM integration in the GUI"""

    @patch('src.gui.llm_integration.extract_vital_signs_rule_based')
    @patch('src.gui.llm_integration.extract_vital_signs_llm')
    def test_extract_patient_data_with_fallback_llm_success(self, mock_llm, mock_rule_based):
        """Test extraction with fallback when LLM is successful"""
        # Mock successful LLM extraction
        mock_llm.return_value = {
            "heart_rate": "130",
            "respiratory_rate": "28",
            "oxygen_saturation": "94",
            "blood_pressure": "90/60",
            "temperature": "38.5C"
        }
        
        # Call function
        result = extract_patient_data_with_fallback(
            "3-year-old with fever, HR 130, RR 28, sats 94%, BP 90/60, temp 38.5C"
        )
        
        # Verify results
        self.assertEqual(result["vital_signs"]["heart_rate"], "130")
        self.assertEqual(result["vital_signs"]["respiratory_rate"], "28")
        self.assertEqual(result["vital_signs"]["oxygen_saturation"], "94")
        self.assertEqual(result["note"], "Extracted using LLM")
        
        # Verify LLM was called but rule-based wasn't
        mock_llm.assert_called_once()
        mock_rule_based.assert_not_called()

    @patch('src.gui.llm_integration.extract_vital_signs_rule_based')
    @patch('src.gui.llm_integration.extract_vital_signs_llm')
    def test_extract_patient_data_with_fallback_llm_failure(self, mock_llm, mock_rule_based):
        """Test extraction with fallback when LLM fails"""
        # Mock LLM failure
        mock_llm.side_effect = Exception("LLM API error")
        
        # Mock rule-based extraction
        mock_rule_based.return_value = {
            "heart_rate": "130",
            "respiratory_rate": "28",
            "oxygen_saturation": "94",
            "blood_pressure": "90/60",
            "temperature": "38.5C"
        }
        
        # Call function
        result = extract_patient_data_with_fallback(
            "3-year-old with fever, HR 130, RR 28, sats 94%, BP 90/60, temp 38.5C"
        )
        
        # Verify results
        self.assertEqual(result["vital_signs"]["heart_rate"], "130")
        self.assertEqual(result["vital_signs"]["respiratory_rate"], "28")
        self.assertEqual(result["vital_signs"]["oxygen_saturation"], "94")
        self.assertEqual(result["note"], "Extracted using rule-based fallback")
        
        # Verify both methods were called
        mock_llm.assert_called_once()
        mock_rule_based.assert_called_once()

    @patch('src.gui.llm_integration.extract_vital_signs_rule_based')
    @patch('src.gui.llm_integration.extract_vital_signs_llm')
    def test_extract_patient_data_with_fallback_both_fail(self, mock_llm, mock_rule_based):
        """Test extraction with fallback when both methods fail"""
        # Mock both methods failing
        mock_llm.side_effect = Exception("LLM API error")
        mock_rule_based.side_effect = Exception("Parsing error")
        
        # Call function
        result = extract_patient_data_with_fallback(
            "Complex patient description with no obvious vital signs"
        )
        
        # Verify results
        self.assertEqual(result["vital_signs"], {})
        self.assertEqual(result["note"], "Extraction failed, no vital signs identified")
        self.assertTrue(result["error"])
        
        # Verify both methods were called
        mock_llm.assert_called_once()
        mock_rule_based.assert_called_once()

    def test_process_llm_extraction(self):
        """Test processing of LLM extraction results"""
        # Test with complete data
        complete_data = {
            "vital_signs": {
                "heart_rate": "150",
                "respiratory_rate": "40",
                "oxygen_saturation": "88",
                "blood_pressure": "90/50"
            },
            "age_years": 3,
            "chief_complaint": "Respiratory distress",
            "note": "Extracted using LLM"
        }
        
        processed = process_llm_extraction(complete_data)
        
        self.assertEqual(processed["heart_rate"], 150)
        self.assertEqual(processed["respiratory_rate"], 40)
        self.assertEqual(processed["oxygen_saturation"], 88)
        self.assertEqual(processed["blood_pressure_systolic"], 90)
        self.assertEqual(processed["blood_pressure_diastolic"], 50)
        
        # Test with partial data
        partial_data = {
            "vital_signs": {
                "heart_rate": "120",
                "respiratory_rate": "25"
                # Missing other vitals
            },
            "age_years": 5,
            "note": "Extracted using rule-based fallback"
        }
        
        partial_processed = process_llm_extraction(partial_data)
        
        self.assertEqual(partial_processed["heart_rate"], 120)
        self.assertEqual(partial_processed["respiratory_rate"], 25)
        self.assertIsNone(partial_processed.get("oxygen_saturation"))
        self.assertIsNone(partial_processed.get("blood_pressure_systolic"))

    def test_determine_care_level(self):
        """Test determination of care level based on vital signs and text analysis"""
        # Test critical case
        critical_vitals = {
            "heart_rate": 160,
            "respiratory_rate": 45,
            "oxygen_saturation": 85,
            "blood_pressure_systolic": 80,
            "age_years": 3
        }
        
        critical_text = "Severe respiratory distress, altered mental status, requiring immediate intervention"
        
        critical_level = determine_care_level(critical_vitals, critical_text)
        self.assertEqual(critical_level, "critical")
        
        # Test intermediate case
        intermediate_vitals = {
            "heart_rate": 130,
            "respiratory_rate": 28,
            "oxygen_saturation": 93,
            "blood_pressure_systolic": 95,
            "age_years": 5
        }
        
        intermediate_text = "Moderate respiratory distress, responsive to treatment, may need admission"
        
        intermediate_level = determine_care_level(intermediate_vitals, intermediate_text)
        self.assertEqual(intermediate_level, "intermediate")
        
        # Test routine case
        routine_vitals = {
            "heart_rate": 105,
            "respiratory_rate": 22,
            "oxygen_saturation": 98,
            "blood_pressure_systolic": 110,
            "age_years": 10
        }
        
        routine_text = "Stable, well-appearing, minor complaint, suitable for routine care"
        
        routine_level = determine_care_level(routine_vitals, routine_text)
        self.assertEqual(routine_level, "routine")
        
        # Test vitals-based determination when text is unclear
        unclear_text = "Patient presenting for evaluation"
        
        vitals_based_level = determine_care_level(critical_vitals, unclear_text)
        self.assertEqual(vitals_based_level, "critical")  # Should still be critical based on vitals


if __name__ == "__main__":
    unittest.main()
