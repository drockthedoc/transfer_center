#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for the integration of pediatric scoring systems in the decision engine.

This module tests how the scoring systems are integrated into the decision-making process,
particularly focusing on automatic care level determination when human suggestions aren't available.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.core.models import Location, PatientData, TransferRequest
from src.core.scoring.score_processor import (
    calculate_all_scores,
    determine_care_level,
    extract_vital_signs,
    process_patient_scores,
)


class TestScoringExtraction(unittest.TestCase):
    """Test the extraction of vital signs from patient data."""

    def test_extract_vitals_complete_data(self):
        """Test extraction with complete structured data."""
        patient = PatientData(
            patient_id="P123",
            clinical_text="",
            extracted_data={
                "age_years": 3,
                "weight_kg": 15.0,
                "respiratory_rate": 25,
                "heart_rate": 120,
                "systolic_bp": 90,
                "diastolic_bp": 60,
                "oxygen_saturation": 96,
            },
        )

        vitals = extract_vital_signs(patient)

        self.assertEqual(vitals.get("age_months"), 36)  # 3 years = 36 months
        self.assertEqual(vitals.get("respiratory_rate"), 25)
        self.assertEqual(vitals.get("heart_rate"), 120)
        self.assertEqual(vitals.get("systolic_bp"), 90)
        self.assertEqual(vitals.get("diastolic_bp"), 60)
        self.assertEqual(vitals.get("oxygen_saturation"), 96)

    def test_extract_vitals_from_notes(self):
        """Test extraction of values from clinical notes."""
        patient = PatientData(
            patient_id="P123",
            extracted_data={
                "age_years": 3,
                "weight_kg": 15.0,
                # Missing vital signs structured data
            },
            clinical_text="Patient presenting with respiratory distress. Respiratory effort is increased. "
            "On high flow oxygen. GCS 14. Capillary refill 2.5 seconds.",
        )

        vitals = extract_vital_signs(patient)

        self.assertEqual(vitals.get("age_months"), 36)
        self.assertEqual(vitals.get("respiratory_effort"), "increased")
        self.assertEqual(vitals.get("oxygen_requirement"), "high flow")
        self.assertEqual(vitals.get("gcs"), 14)
        self.assertEqual(vitals.get("capillary_refill"), 2.5)


class TestScoreCalculation(unittest.TestCase):
    """Test the calculation of pediatric scores."""

    def test_calculate_all_scores(self):
        """Test calculation of all scores for a patient."""
        patient = PatientData(
            patient_id="P123",
            extracted_data={
                "age_years": 3,
                "weight_kg": 15.0,
                "respiratory_rate": 30,
                "heart_rate": 140,
                "systolic_bp": 85,
                "diastolic_bp": 55,
                "oxygen_saturation": 92,
            },
            clinical_text="Patient with respiratory illness. Increased work of breathing. On nasal cannula oxygen. "
            "Alert but irritable. Medical presentation without any injuries.",
        )

        scores = calculate_all_scores(patient)

        # Verify all scoring systems are included
        self.assertIn("pews", scores)
        self.assertIn("trap", scores)
        self.assertIn("chews", scores)
        self.assertIn("tps", scores)
        self.assertIn("queensland_non_trauma", scores)
        self.assertIn("prism3", scores)

        # Check that scores are calculated (not N/A)
        for score_name, score_data in scores.items():
            if score_name != "prism3":  # PRISM3 might be N/A due to missing lab data
                self.assertNotEqual(
                    score_data, "N/A", f"{score_name} should not be N/A"
                )
                if isinstance(score_data, dict) and "score" in score_data:
                    self.assertIsInstance(
                        score_data["score"],
                        (int, float),
                        f"{score_name} score should be numeric",
                    )

    def test_trauma_detection(self):
        """Test detection of trauma cases."""
        trauma_patient = PatientData(
            patient_id="P123",
            extracted_data={
                "age_years": 8,
                "weight_kg": 30.0,
                "respiratory_rate": 22,
                "heart_rate": 110,
                "systolic_bp": 100,
                "diastolic_bp": 70,
                "oxygen_saturation": 98,
            },
            clinical_text="MVC with head injury. Patient alert and oriented. "
            "No respiratory distress.",
        )

        scores = calculate_all_scores(trauma_patient)

        # Verify trauma score is used instead of non-trauma
        self.assertIn("queensland_trauma", scores)
        self.assertNotIn("queensland_non_trauma", scores)


class TestCareLevel(unittest.TestCase):
    """Test determination of care level based on scores."""

    def test_determine_care_level_critical(self):
        """Test care level determination for critical patient."""
        # Mock scores with critical values
        scores = {
            "pews": {"score": 8, "interpretation": "Critical Risk"},
            "trap": {"score": 3, "risk_level": "Critical Risk"},
            "chews": {"score": 9, "alert_level": "Critical Alert Level"},
            "tps": {"score": 7, "risk_level": "Critical Risk"},
            "queensland_non_trauma": {"score": 10, "risk_level": "Critical Risk"},
            "prism3": {"score": 15, "interpretation": "High risk: 15-30% mortality"},
        }

        care_levels, justifications = determine_care_level(scores)

        self.assertIn("PICU", care_levels)
        self.assertTrue(len(justifications) > 0)

    def test_determine_care_level_moderate(self):
        """Test care level determination for moderate severity patient."""
        # Mock scores with moderate values
        scores = {
            "pews": {"score": 3, "interpretation": "Medium Risk"},
            "trap": {"score": 1, "risk_level": "Medium Risk"},
            "chews": {"score": 3, "alert_level": "Medium Alert Level"},
            "tps": {"score": 3, "risk_level": "Moderate Risk"},
            "queensland_non_trauma": {"score": 4, "risk_level": "Medium Risk"},
            "prism3": {"score": 5, "interpretation": "Low risk: <5% mortality"},
        }

        care_levels, justifications = determine_care_level(scores)

        self.assertIn("Intermediate", care_levels)
        self.assertTrue(len(justifications) > 0)

    def test_determine_care_level_low(self):
        """Test care level determination for low severity patient."""
        # Mock scores with low values
        scores = {
            "pews": {"score": 1, "interpretation": "Low Risk"},
            "trap": {"score": 0, "risk_level": "Low Risk"},
            "chews": {"score": 1, "alert_level": "Low Alert Level"},
            "tps": {"score": 1, "risk_level": "Low Risk"},
            "queensland_non_trauma": {"score": 2, "risk_level": "Low Risk"},
            "prism3": {"score": 2, "interpretation": "Low risk: <5% mortality"},
        }

        care_levels, justifications = determine_care_level(scores)

        self.assertIn("General", care_levels)
        self.assertTrue(len(justifications) > 0)


class TestProcessorIntegration(unittest.TestCase):
    """Test the complete scoring processor integration."""

    def test_process_patient_scores(self):
        """Test the complete patient scoring process."""
        patient = PatientData(
            patient_id="P123",
            extracted_data={
                "age_years": 2,
                "age_months": 6,
                "weight_kg": 12.5,
                "respiratory_rate": 40,
                "heart_rate": 155,
                "systolic_bp": 80,
                "diastolic_bp": 50,
                "oxygen_saturation": 91,
            },
            clinical_text="Patient in moderate respiratory distress. Increased work of breathing. "
            "On high flow oxygen. Irritable but consolable.",
        )

        result = process_patient_scores(patient)

        self.assertIn("scores", result)
        self.assertIn("recommended_care_levels", result)
        self.assertIn("justifications", result)

        # With these vital signs, should recommend higher level of care
        self.assertTrue(len(result["recommended_care_levels"]) > 0)
        self.assertTrue(len(result["justifications"]) > 0)


if __name__ == "__main__":
    unittest.main()
