#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for Pediatric Scoring Functions

This module tests the pediatric severity scoring functions to ensure they handle
various scenarios correctly, including:
1. Complete data
2. Missing data
3. Edge cases (extreme values)
"""

import unittest

from src.core.scoring.pediatric import (
    calculate_cameo2,
    calculate_chews,
    calculate_pews,
    calculate_prism3,
    calculate_queensland_non_trauma,
    calculate_queensland_trauma,
    calculate_tps,
    calculate_trap,
)


class TestPEWS(unittest.TestCase):
    """Test cases for the Pediatric Early Warning Score (PEWS)"""

    def test_complete_data(self):
        """Test PEWS calculation with complete data"""
        result = calculate_pews(
            age_months=36,  # 3-year-old
            respiratory_rate=30,
            respiratory_effort="mild",
            oxygen_requirement="nasal cannula",
            heart_rate=130,
            capillary_refill=2.5,
            behavior="irritable",
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result["score"], int)
        self.assertIsNotNone(result["interpretation"])
        self.assertIsNotNone(result["action"])
        self.assertIn("respiratory", result["subscores"])
        self.assertIn("cardiovascular", result["subscores"])
        self.assertIn("behavior", result["subscores"])

    def test_missing_critical_data(self):
        """Test PEWS calculation with missing critical data"""
        result = calculate_pews(
            age_months=36,
            respiratory_rate=None,  # Missing critical parameter
            respiratory_effort="normal",
            oxygen_requirement="none",
            heart_rate=120,
            capillary_refill=1.5,
            behavior="playing",
        )

        self.assertEqual(result["score"], "N/A")
        self.assertIn("missing_parameters", result)
        self.assertIn("respiratory_rate", result["missing_parameters"])

    def test_missing_age(self):
        """Test PEWS calculation with missing age"""
        result = calculate_pews(
            age_months=None,  # Missing age
            respiratory_rate=30,
            respiratory_effort="normal",
            oxygen_requirement="none",
            heart_rate=120,
            capillary_refill=1.5,
            behavior="playing",
        )

        self.assertEqual(result["score"], "N/A")
        self.assertIn("missing_parameters", result)
        self.assertIn("age_months", result["missing_parameters"])

    def test_edge_case_high_values(self):
        """Test PEWS calculation with extremely high values"""
        result = calculate_pews(
            age_months=36,
            respiratory_rate=60,  # Very high for a 3-year-old
            respiratory_effort="severe",
            oxygen_requirement="ventilator",
            heart_rate=180,  # Very high
            capillary_refill=5,  # Delayed
            behavior="unresponsive",
        )

        self.assertIsInstance(result["score"], int)
        self.assertGreaterEqual(result["score"], 6)  # Should be high-risk score

    def test_edge_case_low_values(self):
        """Test PEWS calculation with extremely low values"""
        result = calculate_pews(
            age_months=36,
            respiratory_rate=10,  # Very low for a 3-year-old
            respiratory_effort="normal",
            oxygen_requirement="none",
            heart_rate=60,  # Very low
            capillary_refill=1,
            behavior="playing",
        )

        self.assertIsInstance(result["score"], int)
        self.assertGreaterEqual(
            result["score"], 1
        )  # Should have at least some points for low vitals

    def test_neonate_p_e_w_s(self):
        """Test PEWS for a neonate (e.g., age < 1 month)."""
        result = calculate_pews(
            age_months=0.5, # Neonate
            respiratory_rate=55, # Slightly high for neonate
            respiratory_effort="mild",
            oxygen_requirement="none",
            heart_rate=170, # Slightly high for neonate
            capillary_refill=2,
            behavior="irritable"
        )
        self.assertIsInstance(result["score"], int)
        # Based on typical PEWS, mild tachypnea and tachycardia, plus irritability might give a score around 3-4
        self.assertGreaterEqual(result["score"], 2) 
        self.assertLessEqual(result["score"], 5)
        self.assertIn("Infant", result["normal_ranges"]["heart_rate"]) # Check if age-specific ranges were used

    def test_p_e_w_s_missing_optional_cap_refill(self):
        """Test PEWS when optional capillary_refill is missing."""
        result = calculate_pews(
            age_months=24, # 2 years old
            respiratory_rate=25,
            respiratory_effort="normal",
            oxygen_requirement="none",
            heart_rate=110,
            capillary_refill=None, # Optional
            behavior="playing"
        )
        self.assertIsInstance(result["score"], int)
        self.assertEqual(result["score"], 0) # Should be 0 if all other params are normal


class TestTRAP(unittest.TestCase):
    """Test cases for the Transport Risk Assessment in Pediatrics (TRAP)"""

    def test_complete_data(self):
        """Test TRAP calculation with complete data"""
        result = calculate_trap(
            respiratory_support="nasal cannula",
            respiratory_rate=30,
            work_of_breathing="increased",
            oxygen_saturation=94,
            hemodynamic_stability="stable",
            blood_pressure=90,
            heart_rate=130,
            neuro_status="alert",
            gcs=15,
            access_difficulty="moderate",
            age_months=36,
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result["score"], int)
        self.assertIsNotNone(result["risk_level"])
        self.assertIsNotNone(result["transport_recommendation"])
        self.assertIn("respiratory", result["subscores"])
        self.assertIn("hemodynamic", result["subscores"])
        self.assertIn("neurologic", result["subscores"])
        self.assertIn("access", result["subscores"])

    def test_missing_domain(self):
        """Test TRAP calculation with a missing domain"""
        result = calculate_trap(
            respiratory_support=None,
            respiratory_rate=None,
            work_of_breathing=None,
            oxygen_saturation=None,  # All respiratory parameters missing
            hemodynamic_stability="stable",
            blood_pressure=90,
            heart_rate=130,
            neuro_status="alert",
            gcs=15,
            access_difficulty="easy",
            age_months=36,
        )

        self.assertEqual(result["score"], "N/A")
        self.assertIn("missing_parameters", result)
        self.assertIn("respiratory", result["missing_parameters"])

    def test_minimal_data(self):
        """Test TRAP calculation with minimal data (one param per domain)"""
        result = calculate_trap(
            respiratory_support="high flow",
            respiratory_rate=None,
            work_of_breathing=None,
            oxygen_saturation=None,
            hemodynamic_stability=None,
            blood_pressure=None,
            heart_rate=130,  # Only heart rate for hemodynamic
            neuro_status="voice",  # Only neuro status for neurologic
            gcs=None,
            access_difficulty="difficult",
            age_months=36,
        )

        self.assertIsInstance(result["score"], int)
        self.assertIsNotNone(result["risk_level"])
        self.assertIsNotNone(result["transport_recommendation"])

    def test_edge_case_critical(self):
        """Test TRAP calculation with critical values"""
        result = calculate_trap(
            respiratory_support="ventilator",
            respiratory_rate=None,
            work_of_breathing=None,
            oxygen_saturation=85,
            hemodynamic_stability="unstable",
            blood_pressure=None,
            heart_rate=None,
            neuro_status="unresponsive",
            gcs=None,
            access_difficulty="io",
            age_months=36,
        )

        self.assertIsInstance(result["score"], int)
        self.assertGreaterEqual(result["score"], 3)  # Should be high risk
        self.assertIn("Critical", result["risk_level"])

    def test_trap_missing_age_but_no_age_dependent_vitals(self, mock_get_llm_logger=None): # Add mock for consistency if other tests use it
        """Test TRAP when age is missing but no age-dependent vitals are provided that would require it."""
        result = calculate_trap(
            respiratory_support="ventilator", # Score 3
            oxygen_saturation=85,            # Score 3 (max with support)
            hemodynamic_stability="unstable", # Score 3
            neuro_status="unresponsive",       # Score 3
            access_difficulty="difficult",     # Score 2
            age_months=None 
            # No RR, HR, or BP provided, so age ranges are not strictly needed for these.
        )
        self.assertIsInstance(result["score"], int)
        # Max domain score is 3. Access difficult (2) + max_domain_score >=2 (3) -> adds 1. Total = 4
        self.assertEqual(result["score"], 4) 
        self.assertIn("Critical", result["risk_level"])

    def test_trap_missing_optional_access_difficulty(self, mock_get_llm_logger=None):
        """Test TRAP when optional access_difficulty is missing."""
        result = calculate_trap(
            respiratory_support="none",
            respiratory_rate=30, # Assuming age 36 months, this is normal
            work_of_breathing="normal",
            oxygen_saturation=98,
            hemodynamic_stability="stable",
            blood_pressure=100, # Assuming age 36 months, this is normal
            heart_rate=120,   # Assuming age 36 months, this is normal
            neuro_status="alert",
            gcs=15,
            access_difficulty=None, # Optional
            age_months=36
        )
        self.assertIsInstance(result["score"], int)
        self.assertEqual(result["score"], 0)
        self.assertIn("Low Risk", result["risk_level"])


class TestCAMEO2(unittest.TestCase):
    """Test cases for the CAMEO II scoring system"""

    def test_complete_data(self):
        """Test CAMEO II calculation with complete data"""
        result = calculate_cameo2(
            physiologic_instability=1,
            respiratory_support="nasal cannula",
            oxygen_requirement="low flow",
            cardiovascular_support="stable",
            vitals_frequency="q1h",
            intervention_level="moderate",
            invasive_lines="single central",
            medication_complexity="scheduled iv",
            nursing_dependency="moderate",
            care_requirements="moderate",
            patient_factors="mild",
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result["score"], int)
        self.assertIsNotNone(result["acuity_level"])
        self.assertIsNotNone(result["staffing_recommendation"])

    def test_missing_critical_data(self):
        """Test CAMEO II calculation with missing critical data"""
        result = calculate_cameo2(
            physiologic_instability=None,  # Missing critical parameter
            respiratory_support="nasal cannula",
            oxygen_requirement="low flow",
            cardiovascular_support="stable",
            vitals_frequency="q1h",
            intervention_level="moderate",
            invasive_lines="single central",
            medication_complexity="scheduled iv",
            nursing_dependency="moderate",
            care_requirements="moderate",
            patient_factors="mild",
        )

        self.assertEqual(result["score"], "N/A")
        self.assertIn("missing_parameters", result)
        self.assertIn("physiologic_instability", result["missing_parameters"])

    def test_high_acuity(self):
        """Test CAMEO II calculation with high acuity values"""
        result = calculate_cameo2(
            physiologic_instability=3,
            respiratory_support="ventilator",
            oxygen_requirement="high flow",
            cardiovascular_support="unstable",
            vitals_frequency="continuous",
            intervention_level="intensive",
            invasive_lines="art line",
            medication_complexity="titrated drips",
            nursing_dependency="complete",
            care_requirements="severe",
            patient_factors="critical",
        )

        self.assertIsInstance(result["score"], int)
        self.assertGreaterEqual(result["score"], 25)  # Should be level 3-4
        self.assertIn("Level 4", result["acuity_level"])


class TestPRISM3(unittest.TestCase):
    """Test cases for the PRISM III scoring system"""

    def test_complete_data(self):
        """Test PRISM III calculation with complete data"""
        vitals = {
            "systolic_bp": 80,
            "heart_rate": 120,
            "temperature": 36.5,
            "gcs": 15,
            "pupils": "reactive",
        }

        labs = {
            "ph": 7.35,
            "pco2": 40,
            "po2": 95,
            "bicarbonate": 22,
            "glucose": 100,
            "potassium": 4.0,
            "creatinine": 0.5,
            "bun": 12,
            "wbc": 8.0,
            "platelets": 250,
            "pt": 12,
            "ptt": 30,
        }

        result = calculate_prism3(
            vitals=vitals, labs=labs, age_months=36, ventilated=False
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result["score"], int)
        self.assertIsNotNone(result["interpretation"])
        self.assertIn("cardiovascular", result["subscores"])
        self.assertIn("neurological", result["subscores"])
        self.assertIn("acid_base", result["subscores"])
        self.assertIn("chemistry", result["subscores"])
        self.assertIn("hematologic", result["subscores"])

    def test_missing_vitals_and_labs(self):
        """Test PRISM III calculation with missing vitals and labs"""
        result = calculate_prism3(
            vitals=None, labs=None, age_months=36, ventilated=False
        )

        self.assertEqual(result["score"], "N/A")
        self.assertIn("missing_parameters", result)

    def test_high_risk_values(self):
        """Test PRISM III calculation with high-risk values"""
        vitals = {
            "systolic_bp": 50,  # Very low
            "heart_rate": 180,  # Very high
            "temperature": 32.0,  # Very low
            "gcs": 7,  # Very low
            "pupils": "fixed and dilated",  # Critical
        }

        labs = {
            "ph": 6.9,  # Critical
            "pco2": 80,  # High
            "po2": 50,  # Low
            "bicarbonate": 10,  # Low
            "glucose": 300,  # High
            "potassium": 7.0,  # High
            "creatinine": 2.0,  # High
            "bun": 40,  # High
            "wbc": 2.0,  # Low
            "platelets": 40,  # Low
            "pt": 25,  # High
            "ptt": 60,  # High
        }

        result = calculate_prism3(
            vitals=vitals, labs=labs, age_months=36, ventilated=True
        )

        self.assertIsInstance(result["score"], int)
        self.assertGreaterEqual(result["score"], 30)  # Should be very high risk
        self.assertIn("Very high risk", result["interpretation"])


class TestQueensland(unittest.TestCase):
    """Test cases for the Queensland Pediatric Scoring Systems"""

    def test_non_trauma_complete(self):
        """Test Queensland Non-Trauma calculation with complete data"""
        result = calculate_queensland_non_trauma(
            resp_rate=28,
            HR=125,
            mental_status="alert",
            SpO2=95,
            age_months=36,  # 3-year-old
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result["score"], int)
        self.assertIsNotNone(result["risk_level"])
        self.assertIsNotNone(result["action"])
        self.assertIn("age_category", result)
        self.assertEqual(result["age_category"], "Toddler (1-4 years)")

    def test_non_trauma_missing_data(self):
        """Test Queensland Non-Trauma calculation with missing data"""
        result = calculate_queensland_non_trauma(
            resp_rate=None,  # Missing critical parameter
            HR=125,
            mental_status="alert",
            SpO2=95,
            age_months=36,
        )

        self.assertEqual(result["score"], "N/A")
        self.assertIn("missing_parameters", result)
        self.assertIn("resp_rate", result["missing_parameters"])

    def test_trauma_complete(self):
        """Test Queensland Trauma calculation with complete data"""
        result = calculate_queensland_trauma(
            mechanism="moderate",
            consciousness="alert",
            airway="clear",
            breathing="normal",
            circulation="normal",
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result["score"], int)
        self.assertIsNotNone(result["risk_level"])
        self.assertIsNotNone(result["action"])

    def test_trauma_missing_data(self):
        """Test Queensland Trauma calculation with missing data"""
        result = calculate_queensland_trauma(
            mechanism="severe",
            consciousness="voice",
            airway=None,  # Missing critical parameter
            breathing="distressed",
            circulation="abnormal",
        )

        self.assertEqual(result["score"], "N/A")
        self.assertIn("missing_parameters", result)
        self.assertIn("airway", result["missing_parameters"])

    def test_trauma_high_risk(self):
        """Test Queensland Trauma calculation with high-risk values"""
        result = calculate_queensland_trauma(
            mechanism="critical",
            consciousness="unresponsive",
            airway="unmaintainable",
            breathing="absent",
            circulation="decompensated",
        )

        self.assertIsInstance(result["score"], int)
        self.assertGreaterEqual(result["score"], 12)  # Should be critical risk
        self.assertIn("Critical", result["risk_level"])


class TestTPS(unittest.TestCase):
    """Test cases for the Transport Physiology Score (TPS)"""

    def test_complete_data(self):
        """Test TPS calculation with complete data"""
        result = calculate_tps(
            respiratory_status="mild",
            circulation_status="stable",
            neurologic_status="alert",
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result["score"], int)
        self.assertIsNotNone(result["risk_level"])
        self.assertIsNotNone(result["transport_recommendation"])
        self.assertIn("respiratory", result["subscores"])
        self.assertIn("circulation", result["subscores"])
        self.assertIn("neurologic", result["subscores"])

    def test_missing_all_data(self):
        """Test TPS calculation with all data missing"""
        result = calculate_tps(
            respiratory_status=None, circulation_status=None, neurologic_status=None
        )

        self.assertEqual(result["score"], "N/A")
        self.assertIn("missing_parameters", result)

    def test_partial_data(self):
        """Test TPS calculation with partial data"""
        result = calculate_tps(
            respiratory_status="moderate",
            circulation_status=None,
            neurologic_status=None,
        )

        self.assertIsInstance(result["score"], int)
        self.assertEqual(result["score"], 2)  # Should just have respiratory subscore

    def test_critical_values(self):
        """Test TPS calculation with critical values"""
        result = calculate_tps(
            respiratory_status="severe",
            circulation_status="shock",
            neurologic_status="unresponsive",
        )

        self.assertIsInstance(result["score"], int)
        self.assertEqual(result["score"], 9)  # Maximum score
        self.assertIn("Critical", result["risk_level"])


class TestCHEWS(unittest.TestCase):
    """Test cases for the Children's Hospital Early Warning Score (CHEWS)"""

    def test_complete_data(self):
        """Test CHEWS calculation with complete data"""
        result = calculate_chews(
            respiratory_rate=25,
            respiratory_effort="mild",
            heart_rate=120,
            systolic_bp=90,
            capillary_refill=2,
            oxygen_therapy="nasal cannula",
            oxygen_saturation=95,
            age_months=48,  # 4-year-old
        )

        self.assertIsNotNone(result)
        self.assertIsInstance(result["score"], int)
        self.assertIsNotNone(result["alert_level"])
        self.assertIsNotNone(result["action"])
        self.assertIn("normal_ranges", result)

    def test_missing_critical_data(self):
        """Test CHEWS calculation with missing critical data"""
        result = calculate_chews(
            respiratory_rate=None,  # Missing critical parameter
            respiratory_effort="mild",
            heart_rate=120,
            systolic_bp=90,
            capillary_refill=2,
            oxygen_therapy="nasal cannula",
            oxygen_saturation=95,
            age_months=48,
        )

        self.assertEqual(result["score"], "N/A")
        self.assertIn("missing_parameters", result)
        self.assertIn("respiratory_rate", result["missing_parameters"])

    def test_partial_data(self):
        """Test CHEWS calculation with partial but sufficient data"""
        result = calculate_chews(
            respiratory_rate=25,
            respiratory_effort=None,  # Non-critical parameter missing
            heart_rate=120,
            systolic_bp=None,  # Non-critical parameter missing
            capillary_refill=None,  # Non-critical parameter missing
            oxygen_therapy=None,  # Non-critical parameter missing
            oxygen_saturation=None,  # Non-critical parameter missing
            age_months=48,
        )

        self.assertIsInstance(result["score"], int)
        # Should still calculate with default/zero values for missing non-critical params

    def test_critical_values(self):
        """Test CHEWS calculation with critical values"""
        result = calculate_chews(
            respiratory_rate=10,  # Very low
            respiratory_effort="severe",
            heart_rate=170,  # Very high
            systolic_bp=60,  # Very low
            capillary_refill=5,  # Delayed
            oxygen_therapy="ventilator",
            oxygen_saturation=80,  # Very low
            age_months=48,
        )

        self.assertIsInstance(result["score"], int)
        self.assertGreaterEqual(result["score"], 10)  # Should be critical alert
        self.assertIn("Critical", result["alert_level"])


if __name__ == "__main__":
    unittest.main()
