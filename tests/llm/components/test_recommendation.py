#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for LLM Recommendation Component

This module tests the recommendation generation functionality which synthesizes
patient data, severity scores, and hospital capabilities to produce transfer recommendations.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.llm.components.recommendation import (
    generate_transfer_recommendation,
    prioritize_care_requirements,
    format_recommendation,
    RecommendationGenerator,
)

from src.core.models import LLMReasoningDetails, Recommendation as RecommendationModel


class MockOpenAIClient:
    def __init__(self, response_content):
        self.response_content = response_content
        self.chat = self.Chat()

    class Chat:
        def __init__(self):
            self.completions = self.Completions()

        class Completions:
            def __init__(self):
                self._response_content = None # Will be set by outer class

            def create(self, model, messages, temperature, max_tokens):
                # Access the response_content from the enclosing MockOpenAIClient instance
                mock_choice = MagicMock()
                mock_choice.message.content = self._response_content
                mock_choice.finish_reason = "stop"
                
                mock_usage = MagicMock()
                mock_usage.total_tokens = 100
                mock_usage.prompt_tokens = 50
                mock_usage.completion_tokens = 50

                mock_response = MagicMock()
                mock_response.choices = [mock_choice]
                mock_response.usage = mock_usage
                return mock_response

# Patch the get_llm_logger to avoid issues with its internal state if not configured
@patch('src.llm.components.recommendation.get_llm_logger')
class TestRecommendationGenerator(unittest.TestCase):
    """Test cases for the RecommendationGenerator class."""

    def setUp(self):
        self.sample_extracted_entities = {
            "demographics": {"age": "5 years", "gender": "female"},
            "clinical_information": {"chief_complaint": "fever", "clinical_history": "cough for 3 days"},
            "vital_signs": {"hr": "120", "rr": "30", "bp": "100/60", "temp": "38.5C", "o2": "95%"}
        }
        self.sample_specialty_assessment = {
            "recommended_care_level": "General Pediatrics",
            "required_specialties": ["Pediatrics"],
            "scoring_results": {"scores": {"pews": {"total_score": 2}}}
        }
        self.sample_exclusion_evaluation = {"excluded_campuses": [], "exclusion_reasons": {}}
        self.sample_available_hospitals = [
            {"name": "City General", "campus_id": "CGH", "care_levels": ["General", "ICU"], "specialties": ["Pediatrics"]}
        ]
        self.sample_census_data = {"CGH": {"GENERAL_BEDS": {"available": 10, "total": 20}}}

    def test_successful_recommendation_full_explainability(self, mock_get_llm_logger):
        """Test successful recommendation with full explainability details."""
        mock_llm_logger_instance = MagicMock()
        mock_get_llm_logger.return_value = mock_llm_logger_instance

        llm_response_data = {
            "recommended_campus_id": "CGH",
            "recommended_campus_name": "City General",
            "care_level": "General Pediatrics",
            "confidence_score": 95.0,
            "explainability_details": {
                "main_recommendation_reason": "Excellent pediatric services and bed availability.",
                "alternative_reasons": {"OtherHospital": "Lacks pediatric specialty."},
                "key_factors_considered": ["Pediatric specialty", "Bed availability", "Distance"],
                "confidence_explanation": "High confidence due to direct match of needs."
            },
            "notes": ["Patient stable for transport."],
            "transport_details": {"mode": "GROUND_AMBULANCE", "estimated_time_minutes": 30, "special_requirements": "None"},
            "conditions": {"weather": "Clear", "traffic": "Light"}
        }
        mock_client = MockOpenAIClient(json.dumps(llm_response_data))
        mock_client.chat.completions._response_content = json.dumps(llm_response_data) # Set response content for the mock

        generator = RecommendationGenerator(client=mock_client, model="test-model")
        recommendation = generator.generate_recommendation(
            self.sample_extracted_entities, self.sample_specialty_assessment,
            self.sample_exclusion_evaluation, self.sample_available_hospitals, self.sample_census_data
        )

        self.assertIsInstance(recommendation, RecommendationModel)
        self.assertEqual(recommendation.recommended_campus_id, "CGH")
        self.assertEqual(recommendation.recommended_campus_name, "City General")
        self.assertIsInstance(recommendation.explainability_details, LLMReasoningDetails)
        self.assertEqual(recommendation.explainability_details.main_recommendation_reason, llm_response_data["explainability_details"]["main_recommendation_reason"])
        self.assertEqual(recommendation.explainability_details.alternative_reasons, llm_response_data["explainability_details"]["alternative_reasons"])
        self.assertEqual(recommendation.explainability_details.key_factors_considered, llm_response_data["explainability_details"]["key_factors_considered"])
        self.assertEqual(recommendation.explainability_details.confidence_explanation, llm_response_data["explainability_details"]["confidence_explanation"])
        self.assertEqual(recommendation.notes, llm_response_data["notes"])

    def test_recommendation_incomplete_explainability(self, mock_get_llm_logger):
        """Test recommendation when LLM returns incomplete explainability details."""
        mock_llm_logger_instance = MagicMock()
        mock_get_llm_logger.return_value = mock_llm_logger_instance

        llm_response_data = {
            "recommended_campus_id": "CGH",
            "recommended_campus_name": "City General",
            "care_level": "General Pediatrics",
            "confidence_score": 80.0,
            "explainability_details": {
                "main_recommendation_reason": "Good pediatric services."
                # Missing alternative_reasons, key_factors_considered, confidence_explanation
            }
        }
        mock_client = MockOpenAIClient(json.dumps(llm_response_data))
        mock_client.chat.completions._response_content = json.dumps(llm_response_data)


        generator = RecommendationGenerator(client=mock_client, model="test-model")
        recommendation = generator.generate_recommendation(
            self.sample_extracted_entities, self.sample_specialty_assessment,
            self.sample_exclusion_evaluation, self.sample_available_hospitals, self.sample_census_data
        )

        self.assertIsInstance(recommendation.explainability_details, LLMReasoningDetails)
        self.assertEqual(recommendation.explainability_details.main_recommendation_reason, "Good pediatric services.")
        self.assertEqual(recommendation.explainability_details.alternative_reasons, {}) # Should default
        self.assertEqual(recommendation.explainability_details.key_factors_considered, []) # Should default
        self.assertIsNone(recommendation.explainability_details.confidence_explanation) # Optional

    def test_recommendation_missing_explainability_entirely(self, mock_get_llm_logger):
        """Test recommendation when LLM response misses explainability_details entirely."""
        mock_llm_logger_instance = MagicMock()
        mock_get_llm_logger.return_value = mock_llm_logger_instance
        
        llm_response_data = {
            "recommended_campus_id": "CGH",
            "recommended_campus_name": "City General",
            "care_level": "General Pediatrics",
            "confidence_score": 75.0
            # explainability_details is completely missing
        }
        mock_client = MockOpenAIClient(json.dumps(llm_response_data))
        mock_client.chat.completions._response_content = json.dumps(llm_response_data)

        generator = RecommendationGenerator(client=mock_client, model="test-model")
        recommendation = generator.generate_recommendation(
            self.sample_extracted_entities, self.sample_specialty_assessment,
            self.sample_exclusion_evaluation, self.sample_available_hospitals, self.sample_census_data
        )

        self.assertIsInstance(recommendation.explainability_details, LLMReasoningDetails)
        # Check for default value from LLMReasoningDetails or the validator in Recommendation model
        self.assertIn("Primary reason not specified", recommendation.explainability_details.main_recommendation_reason)
        self.assertEqual(recommendation.explainability_details.alternative_reasons, {})
        self.assertEqual(recommendation.explainability_details.key_factors_considered, [])

    @patch('src.llm.components.recommendation.robust_json_parser', side_effect=json.JSONDecodeError("Simulated Error", "doc", 0))
    def test_llm_processing_failure_json_decode(self, mock_robust_parser, mock_get_llm_logger):
        """Test error handling when LLM response parsing fails (JSONDecodeError)."""
        mock_llm_logger_instance = MagicMock()
        mock_get_llm_logger.return_value = mock_llm_logger_instance

        mock_client = MockOpenAIClient("This is not JSON") # Malformed content
        mock_client.chat.completions._response_content = "This is not JSON"


        generator = RecommendationGenerator(client=mock_client, model="test-model")
        recommendation = generator.generate_recommendation(
            self.sample_extracted_entities, self.sample_specialty_assessment
        )
        
        self.assertEqual(recommendation.recommended_campus_id, "ERROR_PARSING")
        self.assertIsInstance(recommendation.explainability_details, LLMReasoningDetails)
        self.assertIn("Failed to parse LLM response", recommendation.explainability_details.main_recommendation_reason)

    @patch('src.llm.components.recommendation.RecommendationGenerator._standardize_llm_response', side_effect=Exception("Simulated standardization error"))
    def test_llm_processing_failure_standardization(self, mock_standardize, mock_get_llm_logger):
        """Test error handling when standardization fails."""
        mock_llm_logger_instance = MagicMock()
        mock_get_llm_logger.return_value = mock_llm_logger_instance

        llm_response_data = {"recommended_campus_id": "CGH"} # Valid JSON, but assume it causes standardization error
        mock_client = MockOpenAIClient(json.dumps(llm_response_data))
        mock_client.chat.completions._response_content = json.dumps(llm_response_data)

        generator = RecommendationGenerator(client=mock_client, model="test-model")
        recommendation = generator.generate_recommendation(
            self.sample_extracted_entities, self.sample_specialty_assessment
        )
        
        self.assertEqual(recommendation.recommended_campus_id, "ERROR_OUTER_PROCESSING") # Updated based on where error is caught
        self.assertIsInstance(recommendation.explainability_details, LLMReasoningDetails)
        self.assertIn("Critical error processing LLM recommendation", recommendation.explainability_details.main_recommendation_reason)

    def test_recommendation_with_valid_transport_and_conditions(self, mock_get_llm_logger):
        """Test successful recommendation with valid transport_details and conditions."""
        mock_llm_logger_instance = MagicMock()
        mock_get_llm_logger.return_value = mock_llm_logger_instance

        transport_data = {"mode": "Ambulance", "estimated_time_minutes": 30}
        conditions_data = {"weather": "Clear", "traffic": "Light"}
        llm_response_data = {
            "recommended_campus_id": "CGH",
            "recommended_campus_name": "City General",
            "care_level": "General Pediatrics",
            "confidence_score": 90.0,
            "explainability_details": {"main_recommendation_reason": "Reason"},
            "transport_details": transport_data,
            "conditions": conditions_data,
        }
        mock_client = MockOpenAIClient(json.dumps(llm_response_data))
        mock_client.chat.completions._response_content = json.dumps(llm_response_data)

        generator = RecommendationGenerator(client=mock_client, model="test-model")
        
        # Patch the logger inside the _standardize_llm_response to check specific log messages
        with patch.object(generator.logger, 'debug') as mock_logger_debug:
            recommendation = generator.generate_recommendation(
                self.sample_extracted_entities, self.sample_specialty_assessment
            )

            self.assertEqual(recommendation.transport_details, transport_data)
            self.assertEqual(recommendation.conditions, conditions_data)
            
            # Check for specific logging calls (optional, but good practice)
            # This checks if the logger was called with messages containing these substrings.
            # Note: This part of the test relies on the internal logging messages.
            # If these messages change, the test might need updating.
            mock_logger_debug.assert_any_call(f"Raw transport_details from LLM: {transport_data}")
            mock_logger_debug.assert_any_call(f"Standardized transport_details: {transport_data}")
            mock_logger_debug.assert_any_call(f"Raw conditions from LLM: {conditions_data}")
            mock_logger_debug.assert_any_call(f"Standardized conditions: {conditions_data}")
            mock_logger_debug.assert_any_call(f"Data for Recommendation model instantiation (pre-Pydantic):")


    def test_recommendation_missing_transport_and_conditions(self, mock_get_llm_logger):
        """Test recommendation when transport_details and conditions are missing."""
        mock_llm_logger_instance = MagicMock()
        mock_get_llm_logger.return_value = mock_llm_logger_instance

        llm_response_data = {
            "recommended_campus_id": "CGH",
            "recommended_campus_name": "City General",
            "care_level": "General Pediatrics",
            "confidence_score": 85.0,
            "explainability_details": {"main_recommendation_reason": "Reason"},
            # transport_details and conditions are missing
        }
        mock_client = MockOpenAIClient(json.dumps(llm_response_data))
        mock_client.chat.completions._response_content = json.dumps(llm_response_data)
        generator = RecommendationGenerator(client=mock_client, model="test-model")
        
        with patch.object(generator.logger, 'debug') as mock_logger_debug:
            recommendation = generator.generate_recommendation(
                self.sample_extracted_entities, self.sample_specialty_assessment
            )
            self.assertEqual(recommendation.transport_details, {})
            self.assertEqual(recommendation.conditions, {})
            mock_logger_debug.assert_any_call("Raw transport_details from LLM: None")
            mock_logger_debug.assert_any_call("Standardized transport_details: {}")
            mock_logger_debug.assert_any_call("Raw conditions from LLM: None")
            mock_logger_debug.assert_any_call("Standardized conditions: {}")

    def test_recommendation_invalid_type_transport_and_conditions(self, mock_get_llm_logger):
        """Test recommendation when transport_details and conditions are of invalid types."""
        mock_llm_logger_instance = MagicMock()
        mock_get_llm_logger.return_value = mock_llm_logger_instance

        llm_response_data = {
            "recommended_campus_id": "CGH",
            "recommended_campus_name": "City General",
            "care_level": "General Pediatrics",
            "confidence_score": 82.0,
            "explainability_details": {"main_recommendation_reason": "Reason"},
            "transport_details": "Should be a dict",
            "conditions": "Should be a dict"
        }
        mock_client = MockOpenAIClient(json.dumps(llm_response_data))
        mock_client.chat.completions._response_content = json.dumps(llm_response_data)
        generator = RecommendationGenerator(client=mock_client, model="test-model")

        with patch.object(generator.logger, 'warning') as mock_logger_warning, \
             patch.object(generator.logger, 'debug') as mock_logger_debug:
            recommendation = generator.generate_recommendation(
                self.sample_extracted_entities, self.sample_specialty_assessment
            )
            self.assertEqual(recommendation.transport_details, {})
            self.assertEqual(recommendation.conditions, {})
            
            # Verify warnings were logged
            mock_logger_warning.assert_any_call("LLM provided transport_details of type <class 'str'>, expected dict. Defaulting to empty dict.")
            mock_logger_warning.assert_any_call("LLM provided conditions of type <class 'str'>, expected dict. Defaulting to empty dict.")
            
            # Verify debug logs for raw and standardized values
            mock_logger_debug.assert_any_call("Raw transport_details from LLM: Should be a dict")
            mock_logger_debug.assert_any_call("Standardized transport_details: {}")
            mock_logger_debug.assert_any_call("Raw conditions from LLM: Should be a dict")
            mock_logger_debug.assert_any_call("Standardized conditions: {}")


class TestRecommendationComponent(unittest.TestCase):
    """Test cases for the recommendation component"""

    def test_prioritize_care_requirements(self):
        """Test prioritization of care requirements based on severity scores"""
        # Test high severity pediatric case
        patient_data = {
            "patient_demographics": {
                "age_years": 3,
                "weight_kg": 14,
            },
            "vital_signs": {
                "heart_rate": "150",
                "respiratory_rate": "40",
                "oxygen_saturation": "88",
                "temperature": "39.2C",
            },
            "severity_scores": {
                "pews": {"score": 8, "interpretation": "High Risk"},
                "trap": {"score": 9, "interpretation": "High Risk"},
                "chews": {"score": 7, "interpretation": "Critical Alert"}
            },
            "condition": "Respiratory distress, suspected pneumonia"
        }
        
        priorities = prioritize_care_requirements(patient_data)
        
        self.assertEqual(priorities["level_of_care"], "critical")
        self.assertIn("pediatric_icu", priorities["required_services"])
        self.assertIn("pediatric_pulmonology", priorities["specialist_needs"])
        self.assertTrue(priorities["time_sensitive"])
        
        # Test moderate severity case
        moderate_data = {
            "patient_demographics": {
                "age_years": 10,
                "weight_kg": 35,
            },
            "vital_signs": {
                "heart_rate": "110",
                "respiratory_rate": "24",
                "oxygen_saturation": "94",
                "temperature": "38.0C",
            },
            "severity_scores": {
                "pews": {"score": 4, "interpretation": "Medium Risk"},
                "trap": {"score": 5, "interpretation": "Medium Risk"},
                "chews": {"score": 3, "interpretation": "Yellow Alert"}
            },
            "condition": "Uncomplicated appendicitis"
        }
        
        moderate_priorities = prioritize_care_requirements(moderate_data)
        
        self.assertEqual(moderate_priorities["level_of_care"], "intermediate")
        self.assertIn("pediatric_surgery", moderate_priorities["required_services"])
        self.assertFalse(moderate_priorities["time_sensitive"])

    @patch('src.llm.components.recommendation.prioritize_care_requirements')
    def test_generate_transfer_recommendation(self, mock_prioritize):
        """Test generation of transfer recommendations"""
        # Setup mock
        mock_prioritize.return_value = {
            "level_of_care": "critical",
            "required_services": ["pediatric_icu", "pediatric_pulmonology"],
            "specialist_needs": ["pediatric_pulmonologist", "critical_care"],
            "time_sensitive": True
        }
        
        # Test data
        patient_data = {
            "patient_demographics": {"age_years": 3},
            "vital_signs": {"respiratory_rate": "40"},
            "severity_scores": {
                "pews": {"score": 8},
                "trap": {"score": 9}
            },
            "condition": "Respiratory distress"
        }
        
        hospitals = [
            {
                "name": "Children's Medical Center",
                "distance_miles": 15,
                "available_services": ["pediatric_icu", "pediatric_pulmonology", "pediatric_emergency"],
                "capabilities": {"level_of_care": "critical", "pediatric_specific": True},
                "census": {"icu_beds_available": 3}
            },
            {
                "name": "Community Hospital",
                "distance_miles": 5,
                "available_services": ["emergency", "general_pediatrics"],
                "capabilities": {"level_of_care": "intermediate", "pediatric_specific": False},
                "census": {"icu_beds_available": 2}
            }
        ]
        
        transport_options = {
            "ground_ambulance": {"available": True, "estimated_time_minutes": 25},
            "helicopter": {"available": True, "estimated_time_minutes": 10}
        }
        
        # Call function
        result = generate_transfer_recommendation(patient_data, hospitals, transport_options)
        
        # Verify results
        self.assertEqual(result["recommended_hospital"], "Children's Medical Center")
        self.assertEqual(result["recommended_transport"], "helicopter")
        self.assertIn("recommendation_factors", result)
        self.assertIn("severity_assessment", result)
        self.assertIn("alternative_options", result)
        
        # Verify mock was called
        mock_prioritize.assert_called_once_with(patient_data)
        
        # Test with limited hospital options
        limited_hospitals = [
            {
                "name": "Community Hospital",
                "distance_miles": 5,
                "available_services": ["emergency", "general_pediatrics"],
                "capabilities": {"level_of_care": "intermediate", "pediatric_specific": False},
                "census": {"icu_beds_available": 0}
            }
        ]
        
        limited_result = generate_transfer_recommendation(patient_data, limited_hospitals, transport_options)
        
        self.assertEqual(limited_result["recommended_hospital"], "Community Hospital")
        self.assertIn("warning", limited_result)
        self.assertIn("capability_gaps", limited_result)

    def test_format_recommendation(self):
        """Test formatting of recommendation for display"""
        # Test data
        recommendation = {
            "recommended_hospital": "Children's Medical Center",
            "recommended_transport": "helicopter",
            "recommendation_factors": [
                "Patient requires pediatric ICU care",
                "Time-sensitive condition requires rapid transport",
                "Specialized pediatric pulmonology services needed"
            ],
            "severity_assessment": {
                "pews_score": 8,
                "trap_score": 9,
                "overall_severity": "critical"
            },
            "transport_time_estimates": {
                "ground_minutes": 25,
                "air_minutes": 10
            }
        }
        
        patient_info = {
            "age_years": 3,
            "condition": "Respiratory distress, suspected pneumonia",
            "vital_signs": {
                "heart_rate": "150",
                "respiratory_rate": "40",
                "oxygen_saturation": "88"
            }
        }
        
        # Call function
        formatted = format_recommendation(recommendation, patient_info)
        
        # Verify results
        self.assertIn("RECOMMENDED HOSPITAL", formatted)
        self.assertIn("Children's Medical Center", formatted)
        self.assertIn("TRANSPORT RECOMMENDATION", formatted)
        self.assertIn("helicopter", formatted)
        self.assertIn("SEVERITY ASSESSMENT", formatted)
        self.assertIn("critical", formatted)
        self.assertIn("PATIENT INFORMATION", formatted)
        self.assertIn("RECOMMENDATION FACTORS", formatted)


if __name__ == "__main__":
    unittest.main()
