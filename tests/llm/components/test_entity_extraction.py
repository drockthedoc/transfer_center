#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for LLM Entity Extraction Component

This module tests the entity extraction functionality which uses LLM and rule-based
approaches to extract key information from patient descriptions.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.llm.components.entity_extraction import (
    extract_patient_data,
    extract_vital_signs,
    extract_care_requirements,
    extract_severity_indicators,
)


class TestEntityExtraction(unittest.TestCase):
    """Test cases for the entity extraction component"""

    def test_extract_vital_signs_regex(self):
        """Test extraction of vital signs using regex fallback"""
        # Test with standard vital sign formats
        text = "Patient presents with HR 120, BP 90/60, RR 28, Temp 38.5C, O2 94% on RA."
        vitals = extract_vital_signs(text, use_llm=False)
        
        self.assertEqual(vitals["heart_rate"], "120")
        self.assertEqual(vitals["blood_pressure"], "90/60")
        self.assertEqual(vitals["respiratory_rate"], "28")
        self.assertEqual(vitals["temperature"], "38.5C")
        self.assertEqual(vitals["oxygen_saturation"], "94")
        self.assertEqual(vitals["oxygen_requirement"], "RA")
        
        # Test with varied formats
        varied_text = "Vitals: Heart rate 130 bpm, Blood pressure 100/70 mmHg, Resp rate 30/min, SpO2 92%."
        varied_vitals = extract_vital_signs(varied_text, use_llm=False)
        
        self.assertEqual(varied_vitals["heart_rate"], "130")
        self.assertEqual(varied_vitals["blood_pressure"], "100/70")
        self.assertEqual(varied_vitals["respiratory_rate"], "30")
        self.assertEqual(varied_vitals["oxygen_saturation"], "92")

    @patch('src.llm.components.entity_extraction.llm_client')
    def test_extract_vital_signs_llm(self, mock_llm):
        """Test extraction of vital signs using LLM"""
        # Mock LLM response
        mock_llm.extract_vitals.return_value = {
            "heart_rate": "125",
            "blood_pressure": "95/65",
            "respiratory_rate": "32",
            "temperature": "39.0C",
            "oxygen_saturation": "93",
            "oxygen_requirement": "2L NC"
        }
        
        # Test with complex description
        text = "5yo male presents with increased work of breathing, tachypneic with RR in the 30s, heart racing around 120-130, low-grade fever, sats hovering in the low 90s on 2L NC."
        vitals = extract_vital_signs(text, use_llm=True)
        
        self.assertEqual(vitals["heart_rate"], "125")
        self.assertEqual(vitals["respiratory_rate"], "32")
        self.assertEqual(vitals["oxygen_saturation"], "93")
        self.assertEqual(vitals["oxygen_requirement"], "2L NC")
        
        # Verify LLM was called
        mock_llm.extract_vitals.assert_called_once_with(text)

    @patch('src.llm.components.entity_extraction.llm_client')
    def test_extract_care_requirements(self, mock_llm):
        """Test extraction of care requirements"""
        # Mock LLM response
        mock_llm.extract_care_requirements.return_value = {
            "level_of_care": "picu",
            "specialist_needs": ["pediatric pulmonology", "critical care"],
            "required_equipment": ["ventilator", "high flow oxygen"],
            "isolation_required": False
        }
        
        # Test data
        text = "Patient is in respiratory distress with severe bronchiolitis, may need ventilatory support. Currently on high flow oxygen with poor response."
        
        # Call function
        care_reqs = extract_care_requirements(text)
        
        # Verify results
        self.assertEqual(care_reqs["level_of_care"], "picu")
        self.assertIn("pediatric pulmonology", care_reqs["specialist_needs"])
        self.assertIn("ventilator", care_reqs["required_equipment"])
        
        # Verify LLM was called
        mock_llm.extract_care_requirements.assert_called_once_with(text)

    @patch('src.llm.components.entity_extraction.llm_client')
    def test_llm_fallback_to_regex(self, mock_llm):
        """Test fallback to regex when LLM fails"""
        # Mock LLM failure
        mock_llm.extract_vitals.side_effect = Exception("LLM API error")
        
        # Test data
        text = "Patient presents with HR 120, BP 90/60, RR 28, Temp 38.5C, O2 94% on RA."
        
        # Call function with LLM requested but should fall back
        vitals = extract_vital_signs(text, use_llm=True)
        
        # Verify results - should have regex results
        self.assertEqual(vitals["heart_rate"], "120")
        self.assertEqual(vitals["blood_pressure"], "90/60")
        self.assertEqual(vitals["respiratory_rate"], "28")
        self.assertEqual(vitals["oxygen_saturation"], "94")
        self.assertEqual(vitals["note"], "Extracted using rule-based fallback")
        
        # Verify LLM was called but failed
        mock_llm.extract_vitals.assert_called_once()

    @patch('src.llm.components.entity_extraction.extract_vital_signs')
    @patch('src.llm.components.entity_extraction.extract_care_requirements')
    @patch('src.llm.components.entity_extraction.extract_severity_indicators')
    def test_extract_patient_data_integration(self, mock_severity, mock_care, mock_vitals):
        """Test the main extract_patient_data function integration"""
        # Setup mocks
        mock_vitals.return_value = {
            "heart_rate": "120",
            "respiratory_rate": "30",
            "note": "Extracted using LLM"
        }
        mock_care.return_value = {
            "level_of_care": "picu",
            "specialist_needs": ["pediatric pulmonology"]
        }
        mock_severity.return_value = {
            "critical_indicators": ["respiratory distress"],
            "severity_level": "high"
        }
        
        # Test data
        text = "3-year-old with severe respiratory distress, suspected RSV bronchiolitis."
        
        # Call function
        result = extract_patient_data(text, use_llm=True)
        
        # Verify results
        self.assertIn("vital_signs", result)
        self.assertEqual(result["vital_signs"]["heart_rate"], "120")
        self.assertEqual(result["care_requirements"]["level_of_care"], "picu")
        self.assertEqual(result["severity_assessment"]["severity_level"], "high")
        self.assertIn("patient_demographics", result)
        self.assertIn("raw_text", result)
        
        # Verify mocks were called
        mock_vitals.assert_called_once()
        mock_care.assert_called_once()
        mock_severity.assert_called_once()


if __name__ == "__main__":
    unittest.main()
