"""
Unit tests for the core data models in the Transfer Center application.

Tests ensure proper functionality of:
- TransferRequest property accessors and transport_info dictionary usage
- Recommendation model with all UI-required fields
- HospitalCampus model with distance calculations and care level/specialty checks
"""

import math
import unittest
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.core.models import (
    BedCensus,
    CareLevel,
    HospitalCampus,
    Location,
    PatientData,
    Recommendation,
    Specialty,
    TransferRequest,
    TransportMode,
)


class TestTransferRequest(unittest.TestCase):
    """Tests for the TransferRequest model and its property accessors."""

    def setUp(self):
        """Set up test data for each test case."""
        self.patient_data = PatientData(
            patient_id="TEST123",
            clinical_text="Test patient with fever",
            care_level="General",
        )
        self.location = Location(latitude=29.7604, longitude=-95.3698)  # Houston coordinates

    def test_transport_info_initialization(self):
        """Test that transport_info is properly initialized."""
        # Test with default empty transport_info
        request = TransferRequest(
            request_id="REQ123",
            patient_data=self.patient_data,
            sending_location=self.location,
        )
        self.assertEqual(request.transport_info, {})

        # Test with provided transport_info
        info = {"clinical_text": "Sample text", "scoring_results": {"PEWS": 3}}
        request = TransferRequest(
            request_id="REQ123",
            patient_data=self.patient_data,
            sending_location=self.location,
            transport_info=info,
        )
        self.assertEqual(request.transport_info, info)

    def test_clinical_text_property(self):
        """Test the clinical_text property accessor."""
        request = TransferRequest(
            request_id="REQ123",
            patient_data=self.patient_data,
            sending_location=self.location,
        )
        
        # Initial value should be empty string
        self.assertEqual(request.clinical_text, "")
        
        # Set a value
        test_text = "Patient presents with respiratory distress"
        request.clinical_text = test_text
        
        # Value should be accessible via property and in transport_info
        self.assertEqual(request.clinical_text, test_text)
        self.assertEqual(request.transport_info["clinical_text"], test_text)

    def test_scoring_results_property(self):
        """Test the scoring_results property accessor."""
        request = TransferRequest(
            request_id="REQ123",
            patient_data=self.patient_data,
            sending_location=self.location,
        )
        
        # Initial value should be empty dict
        self.assertEqual(request.scoring_results, {})
        
        # Set a value
        test_scores = {"PEWS": 3, "TRAP": {"respiratory": 2, "total": 5}}
        request.scoring_results = test_scores
        
        # Value should be accessible via property and in transport_info
        self.assertEqual(request.scoring_results, test_scores)
        self.assertEqual(request.transport_info["scoring_results"], test_scores)

    def test_human_suggestions_property(self):
        """Test the human_suggestions property accessor."""
        request = TransferRequest(
            request_id="REQ123",
            patient_data=self.patient_data,
            sending_location=self.location,
        )
        
        # Initial value should be empty dict
        self.assertEqual(request.human_suggestions, {})
        
        # Set a value
        test_suggestions = {"preferred_hospital": "Children's Hospital"}
        request.human_suggestions = test_suggestions
        
        # Value should be accessible via property and in transport_info
        self.assertEqual(request.human_suggestions, test_suggestions)
        self.assertEqual(request.transport_info["human_suggestions"], test_suggestions)

    def test_sending_facility_location_compatibility(self):
        """Test backward compatibility for sending_facility_location property."""
        # Create with sending_location
        request = TransferRequest(
            request_id="REQ123",
            patient_data=self.patient_data,
            sending_location=self.location,
        )
        
        # Should be accessible via both properties
        self.assertEqual(request.sending_location, self.location)
        self.assertEqual(request.sending_facility_location, self.location)
        
        # Set via compatibility property
        new_location = Location(latitude=30.2672, longitude=-97.7431)  # Austin
        request.sending_facility_location = new_location
        
        # Should update the actual field
        self.assertEqual(request.sending_location, new_location)

    def test_get_transport_info_value(self):
        """Test the get_transport_info_value helper method."""
        request = TransferRequest(
            request_id="REQ123",
            patient_data=self.patient_data,
            sending_location=self.location,
            transport_info={"key1": "value1", "key2": 123},
        )
        
        # Existing keys
        self.assertEqual(request.get_transport_info_value("key1"), "value1")
        self.assertEqual(request.get_transport_info_value("key2"), 123)
        
        # Non-existent key with default
        self.assertEqual(request.get_transport_info_value("key3", "default"), "default")
        
        # Non-existent key without default
        self.assertIsNone(request.get_transport_info_value("key3"))
        
        # Edge case: transport_info is None (shouldn't happen with our changes)
        request.transport_info = None
        self.assertEqual(request.get_transport_info_value("key1", "fallback"), "fallback")

    def test_set_transport_info_value(self):
        """Test the set_transport_info_value helper method."""
        request = TransferRequest(
            request_id="REQ123",
            patient_data=self.patient_data,
            sending_location=self.location,
        )
        
        # Set a value
        request.set_transport_info_value("test_key", "test_value")
        self.assertEqual(request.transport_info["test_key"], "test_value")
        
        # Overwrite existing value
        request.set_transport_info_value("test_key", "new_value")
        self.assertEqual(request.transport_info["test_key"], "new_value")
        
        # Edge case: transport_info is None (shouldn't happen with our changes)
        request.transport_info = None
        request.set_transport_info_value("another_key", 123)
        self.assertEqual(request.transport_info, {"another_key": 123})


class TestRecommendation(unittest.TestCase):
    """Tests for the Recommendation model."""

    def setUp(self):
        """Set up test data for each test case."""
        self.patient_data = PatientData(
            patient_id="TEST123",
            clinical_text="Test patient with respiratory issues",
            care_level="General",
        )
        self.recommendation = Recommendation(
            transfer_request_id="REQ123",
            recommended_campus_id="CAMPUS456",
            recommended_campus_name="Test Hospital",
            reason="Most appropriate pediatric care available",
        )

    def test_confidence_score_validation(self):
        """Test that confidence score is properly validated and normalized."""
        # Default value
        self.assertEqual(self.recommendation.confidence_score, 0.0)
        
        # Valid values - create a new instance to test validation
        rec = Recommendation(
            transfer_request_id="REQ123",
            recommended_campus_id="CAMPUS456",
            recommended_campus_name="Test Hospital",
            reason="Most appropriate pediatric care available",
            confidence_score=50.0
        )
        self.assertEqual(rec.confidence_score, 50.0)
        
        # Test validation errors for out-of-range values
        # Lower bound check - Pydantic validation should prevent values < 0
        with pytest.raises(ValidationError):
            Recommendation(
                transfer_request_id="REQ123",
                recommended_campus_id="CAMPUS456",
                reason="Test reason",
                confidence_score=-10.0
            )
        
        # Upper bound - Values > 100 should be rejected or clamped
        # If we've set the upper bound constraint with le=100.0
        with pytest.raises(ValidationError):
            Recommendation(
                transfer_request_id="REQ123",
                recommended_campus_id="CAMPUS456",
                reason="Test reason",
                confidence_score=150.0
            )
        
        # None should be converted to default value (0.0)
        rec_none = Recommendation(
            transfer_request_id="REQ123",
            recommended_campus_id="CAMPUS456",
            reason="Test reason",
            confidence_score=None
        )
        self.assertEqual(rec_none.confidence_score, 0.0)

    def test_explainability_details_structure(self):
        """Test that explainability_details has the proper structure."""
        # Default structure should be initialized
        self.assertIn("factors_considered", self.recommendation.explainability_details)
        self.assertIn("alternative_options", self.recommendation.explainability_details)
        self.assertIn("decision_points", self.recommendation.explainability_details)
        self.assertIn("score_utilization", self.recommendation.explainability_details)
        self.assertIn("distance_factors", self.recommendation.explainability_details)
        self.assertIn("exclusion_reasons", self.recommendation.explainability_details)
        
        # Lists should be empty by default
        self.assertEqual(self.recommendation.explainability_details["factors_considered"], [])
        
        # Test initialization with None
        rec_none = Recommendation(
            transfer_request_id="REQ123",
            recommended_campus_id="CAMPUS456",
            reason="Test reason",
            explainability_details=None
        )
        self.assertIn("factors_considered", rec_none.explainability_details)
        
        # Test initialization with partial data
        rec_partial = Recommendation(
            transfer_request_id="REQ123",
            recommended_campus_id="CAMPUS456",
            reason="Test reason",
            explainability_details={
                "factors_considered": ["Factor 1", "Factor 2"]
            }
        )
        self.assertEqual(
            rec_partial.explainability_details["factors_considered"],
            ["Factor 1", "Factor 2"]
        )
        self.assertIn("alternative_options", rec_partial.explainability_details)

    def test_transport_weather_traffic_info_properties(self):
        """Test the has_transport_weather_info and has_transport_traffic_info properties."""
        # Default values
        self.assertFalse(self.recommendation.has_transport_weather_info)
        self.assertFalse(self.recommendation.has_transport_traffic_info)
        
        # Set weather info
        self.recommendation.conditions = {
            "weather": {"condition": "Clear", "temperature": 75}
        }
        self.assertTrue(self.recommendation.has_transport_weather_info)
        self.assertFalse(self.recommendation.has_transport_traffic_info)
        
        # Set traffic info
        self.recommendation.conditions = {
            "traffic": {"congestion": "Light", "incidents": 0}
        }
        self.assertFalse(self.recommendation.has_transport_weather_info)
        self.assertTrue(self.recommendation.has_transport_traffic_info)
        
        # Set both
        self.recommendation.conditions = {
            "weather": {"condition": "Clear"},
            "traffic": {"congestion": "Light"}
        }
        self.assertTrue(self.recommendation.has_transport_weather_info)
        self.assertTrue(self.recommendation.has_transport_traffic_info)

    def test_get_travel_time_estimate(self):
        """Test the get_travel_time_estimate method."""
        # Default without estimated time
        self.assertEqual(self.recommendation.get_travel_time_estimate(), "Unknown")
        
        # Minutes only
        self.recommendation.transport_details = {"estimated_time_minutes": 45}
        self.assertEqual(self.recommendation.get_travel_time_estimate(), "45 min")
        
        # Hours and minutes
        self.recommendation.transport_details = {"estimated_time_minutes": 90}
        self.assertEqual(self.recommendation.get_travel_time_estimate(), "1 hr 30 min")
        
        # Multiple hours
        self.recommendation.transport_details = {"estimated_time_minutes": 150}
        self.assertEqual(self.recommendation.get_travel_time_estimate(), "2 hr 30 min")

    def test_infer_recommended_level_of_care(self):
        """Test the infer_recommended_level_of_care method."""
        # Default case - already has a value
        self.recommendation.recommended_level_of_care = "PICU"
        self.assertEqual(
            self.recommendation.infer_recommended_level_of_care(self.patient_data),
            "PICU"
        )
        
        # Get from patient data
        self.recommendation.recommended_level_of_care = "General"
        self.patient_data.care_level = "ICU"
        self.assertEqual(
            self.recommendation.infer_recommended_level_of_care(self.patient_data),
            "ICU"
        )
        
        # Infer from explainability factors
        self.recommendation.recommended_level_of_care = "General"
        self.patient_data.care_level = "General"
        self.recommendation.explainability_details = {
            "factors_considered": ["Patient requires PICU care due to respiratory distress"]
        }
        self.assertEqual(
            self.recommendation.infer_recommended_level_of_care(self.patient_data),
            "PICU"
        )
        
        # Test NICU inference
        self.recommendation.recommended_level_of_care = "General"
        self.recommendation.explainability_details = {
            "factors_considered": ["Newborn requires NICU monitoring"]
        }
        self.assertEqual(
            self.recommendation.infer_recommended_level_of_care(self.patient_data),
            "NICU"
        )


class TestHospitalCampus(unittest.TestCase):
    """Tests for the HospitalCampus model."""

    def setUp(self):
        """Set up test data for each test case."""
        self.houston_loc = Location(latitude=29.7604, longitude=-95.3698)
        self.austin_loc = Location(latitude=30.2672, longitude=-97.7431)
        
        self.campus = HospitalCampus(
            campus_id="CAMPUS123",
            name="Test Hospital",
            location=self.houston_loc,
            bed_census=BedCensus(
                total_beds=100,
                available_beds=20,
                icu_beds_total=20,
                icu_beds_available=5,
                picu_beds_total=10,
                picu_beds_available=3,
                nicu_beds_total=15,
                nicu_beds_available=2,
            ),
            care_levels=[CareLevel.GENERAL, CareLevel.ICU, CareLevel.PICU],
            specialties=[Specialty.GENERAL_MEDICINE, Specialty.PEDIATRICS],
        )

    def test_calculate_distance(self):
        """Test the Haversine distance calculation method."""
        # Distance from Houston to Austin is approximately 234 km
        distance = self.campus.calculate_distance(self.austin_loc)
        self.assertAlmostEqual(distance, 234.0, delta=5.0)  # Allow 5km margin of error
        
        # Distance to self should be 0
        distance = self.campus.calculate_distance(self.houston_loc)
        self.assertAlmostEqual(distance, 0.0, delta=0.01)

    def test_calculate_driving_distance(self):
        """Test the driving distance estimation method."""
        # Driving distance should be approximately 30% more than straight-line distance
        straight_line = self.campus.calculate_distance(self.austin_loc)
        driving = self.campus.calculate_driving_distance_km(self.austin_loc)
        self.assertAlmostEqual(driving, straight_line * 1.3, delta=0.1)

    def test_estimate_driving_time(self):
        """Test the driving time estimation method."""
        # Base time at 60km/h
        base_time = self.campus.estimate_driving_time_minutes(self.austin_loc)
        # Expected time based on ~234km distance at 60km/h = ~234 minutes
        self.assertAlmostEqual(base_time, 234, delta=15)  # Allow some margin
        
        # With heavy traffic (factor of 2.0)
        heavy_traffic_time = self.campus.estimate_driving_time_minutes(
            self.austin_loc, traffic_factor=2.0
        )
        self.assertAlmostEqual(heavy_traffic_time, base_time * 2, delta=1)

    def test_has_care_level(self):
        """Test the has_care_level method."""
        # Levels present in the campus
        self.assertTrue(self.campus.has_care_level(CareLevel.GENERAL))
        self.assertTrue(self.campus.has_care_level(CareLevel.ICU))
        self.assertTrue(self.campus.has_care_level(CareLevel.PICU))
        
        # Level not present
        self.assertFalse(self.campus.has_care_level(CareLevel.NICU))
        
        # String representation
        self.assertTrue(self.campus.has_care_level("General"))
        self.assertTrue(self.campus.has_care_level("ICU"))
        self.assertTrue(self.campus.has_care_level("PICU"))
        self.assertFalse(self.campus.has_care_level("NICU"))

    def test_has_specialty(self):
        """Test the has_specialty method."""
        # Specialties present in the campus
        self.assertTrue(self.campus.has_specialty(Specialty.GENERAL_MEDICINE))
        self.assertTrue(self.campus.has_specialty(Specialty.PEDIATRICS))
        
        # Specialty not present
        self.assertFalse(self.campus.has_specialty(Specialty.CARDIOLOGY))
        
        # String representation
        self.assertTrue(self.campus.has_specialty("General Medicine"))
        self.assertTrue(self.campus.has_specialty("Pediatrics"))
        self.assertFalse(self.campus.has_specialty("Cardiology"))


if __name__ == "__main__":
    unittest.main()
