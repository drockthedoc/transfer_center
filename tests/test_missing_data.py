#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test missing data handling in pediatric severity scores

This script tests all pediatric severity scoring functions to ensure
they properly handle missing data by returning 'N/A' when appropriate
rather than making unreasonable assumptions.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from docs.pediatric_severity_scores import (
    calculate_cameo2,
    calculate_chews,
    calculate_pews,
    calculate_prism3,
    calculate_queensland_non_trauma,
    calculate_queensland_trauma,
    calculate_tps,
    calculate_trap,
)


def print_header(title):
    """Print a formatted header for test results"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)


def print_result(test_name, result):
    """Print test result in a formatted way"""
    print(f"\n--- {test_name} ---")
    for key, value in result.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for subkey, subvalue in value.items():
                print(f"  {subkey}: {subvalue}")
        else:
            print(f"{key}: {value}")


def test_pews_missing_data():
    """Test PEWS with missing data"""
    print_header("PEWS Missing Data Tests")

    # Test with all parameters missing
    result = calculate_pews()
    print_result("All parameters missing", result)

    # Test with only age provided
    result = calculate_pews(age_months=36)
    print_result("Only age provided", result)

    # Test with some critical parameters missing
    result = calculate_pews(
        age_months=36,
        respiratory_rate=30,
        respiratory_effort="mild",
        heart_rate=None,  # Missing critical parameter
        behavior="playing",
    )
    print_result("Some critical parameters missing", result)

    # Test with all required parameters
    result = calculate_pews(
        age_months=36,
        respiratory_rate=30,
        respiratory_effort="mild",
        heart_rate=110,
        behavior="playing",
    )
    print_result("All required parameters provided", result)


def test_trap_missing_data():
    """Test TRAP with missing data"""
    print_header("TRAP Missing Data Tests")

    # Test with all parameters missing
    result = calculate_trap()
    print_result("All parameters missing", result)

    # Test with some critical parameters missing
    result = calculate_trap(
        respiratory_support="nasal cannula",
        hemodynamic_stability=None,  # Missing critical parameter
        neuro_status="normal",
        access_difficulty="no",
    )
    print_result("Some critical parameters missing", result)

    # Test with all required parameters
    result = calculate_trap(
        respiratory_support="nasal cannula",
        hemodynamic_stability="stable",
        neuro_status="normal",
        access_difficulty="no",
    )
    print_result("All required parameters provided", result)


def test_prism3_missing_data():
    """Test PRISM III with missing data"""
    print_header("PRISM III Missing Data Tests")

    # Test with all parameters missing
    result = calculate_prism3()
    print_result("All parameters missing", result)

    # Test with vitals but no labs
    result = calculate_prism3(vitals={"SBP": 90, "HR": 120, "GCS": 15}, labs=None)
    print_result("Vitals provided but no labs", result)

    # Test with complete data
    result = calculate_prism3(
        vitals={"SBP": 90, "HR": 120, "GCS": 15},
        labs={"pH": 7.35, "glucose": 110, "potassium": 4.0, "creatinine": 0.5},
        age_months=48,
    )
    print_result("Complete data provided", result)


def test_queensland_missing_data():
    """Test Queensland scores with missing data"""
    print_header("Queensland Scores Missing Data Tests")

    # Test non-trauma score with missing data
    result = calculate_queensland_non_trauma(
        resp_rate=None, HR=120, mental_status="alert", SpO2=98
    )
    print_result("Queensland Non-Trauma with missing data", result)

    # Test trauma score with missing critical data
    result = calculate_queensland_trauma(
        mechanism=None,  # Missing critical parameter
        consciousness="alert",
        airway="patent",
        breathing="normal",
        circulation="good perfusion",
    )
    print_result("Queensland Trauma with missing critical data", result)

    # Test trauma score with missing non-critical data
    result = calculate_queensland_trauma(
        mechanism="fall >3m",
        consciousness=None,  # Missing non-critical parameter
        airway="patent",
        breathing=None,  # Missing non-critical parameter
        circulation=None,  # Missing non-critical parameter
    )
    print_result("Queensland Trauma with missing non-critical data", result)


def test_tps_missing_data():
    """Test TPS with missing data"""
    print_header("TPS Missing Data Tests")

    # Test with all parameters missing
    result = calculate_tps()
    print_result("All parameters missing", result)

    # Test with some parameters missing
    result = calculate_tps(
        respiratory_status="moderate",
        circulation_status=None,
        neurologic_status="normal",
    )
    print_result("Some parameters missing", result)


def test_chews_missing_data():
    """Test CHEWS with missing data"""
    print_header("CHEWS Missing Data Tests")

    # Test with critical parameters missing
    result = calculate_chews(
        respiratory_rate=None,  # Missing critical parameter
        heart_rate=120,
        respiratory_effort="normal",
        systolic_bp=100,
        capillary_refill=2,
        oxygen_therapy="none",
        oxygen_saturation=98,
    )
    print_result("Critical parameter missing", result)

    # Test with too many parameters missing
    result = calculate_chews(
        respiratory_rate=30,
        heart_rate=120,
        respiratory_effort=None,
        systolic_bp=None,
        capillary_refill=None,
        oxygen_therapy=None,
        oxygen_saturation=None,
    )
    print_result("Too many parameters missing", result)

    # Test with acceptable missing parameters
    result = calculate_chews(
        respiratory_rate=30,
        heart_rate=120,
        respiratory_effort="mild",
        systolic_bp=None,  # Can be reasonably assumed
        capillary_refill=None,  # Can be reasonably assumed
        oxygen_therapy="low flow",
        oxygen_saturation=94,
    )
    print_result("Acceptable missing parameters", result)


def run_all_tests():
    """Run all test functions"""
    test_pews_missing_data()
    test_trap_missing_data()
    test_prism3_missing_data()
    test_queensland_missing_data()
    test_tps_missing_data()
    test_chews_missing_data()


if __name__ == "__main__":
    run_all_tests()
