#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for Hospital Search Functionality

This module tests the hospital search functionality which allows users to
search for hospitals by name or address and geocodes locations.
"""

import unittest
from unittest.mock import patch, MagicMock, PropertyMock

from src.gui.hospital_search import (
    search_hospitals,
    geocode_address,
    format_hospital_results,
)


class TestHospitalSearch(unittest.TestCase):
    """Test cases for the hospital search functionality"""

    @patch('src.gui.hospital_search.requests.get')
    def test_search_hospitals_by_name(self, mock_get):
        """Test searching for hospitals by name"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "name": "Children's Medical Center",
                    "address": "1935 Medical District Dr, Dallas, TX 75235",
                    "coordinates": {"lat": 32.8099, "lng": -96.8294},
                    "facility_type": "Hospital",
                    "services": ["pediatric_emergency", "pediatric_icu", "trauma_level_1"]
                },
                {
                    "name": "Children's Medical Center Plano",
                    "address": "7601 Preston Rd, Plano, TX 75024",
                    "coordinates": {"lat": 33.0827, "lng": -96.8053},
                    "facility_type": "Hospital",
                    "services": ["pediatric_emergency", "pediatric_icu"]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Call function
        results = search_hospitals(query="Children's Medical", search_type="name")
        
        # Verify results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["name"], "Children's Medical Center")
        self.assertEqual(results[1]["name"], "Children's Medical Center Plano")
        self.assertIn("coordinates", results[0])
        self.assertIn("services", results[0])
        
        # Verify API was called correctly
        mock_get.assert_called_once()
        self.assertIn("name=Children%27s+Medical", mock_get.call_args[0][0])

    @patch('src.gui.hospital_search.requests.get')
    def test_search_hospitals_by_address(self, mock_get):
        """Test searching for hospitals by address"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "name": "Medical City Dallas",
                    "address": "7777 Forest Lane, Dallas, TX 75230",
                    "coordinates": {"lat": 32.9112, "lng": -96.7665},
                    "facility_type": "Hospital",
                    "services": ["emergency", "trauma_level_2"]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Call function
        results = search_hospitals(query="Forest Lane, Dallas", search_type="address")
        
        # Verify results
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Medical City Dallas")
        self.assertEqual(results[0]["address"], "7777 Forest Lane, Dallas, TX 75230")
        
        # Verify API was called correctly
        mock_get.assert_called_once()
        self.assertIn("address=Forest+Lane%2C+Dallas", mock_get.call_args[0][0])

    @patch('src.gui.hospital_search.requests.get')
    def test_search_hospitals_api_error(self, mock_get):
        """Test error handling when API returns an error"""
        # Mock API error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        # Call function
        results = search_hospitals(query="Invalid Query", search_type="name")
        
        # Verify error handling
        self.assertEqual(results, [])

    @patch('src.gui.hospital_search.requests.get')
    def test_geocode_address(self, mock_get):
        """Test geocoding of addresses to coordinates"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "formatted_address": "1935 Medical District Dr, Dallas, TX 75235, USA",
                    "geometry": {
                        "location": {"lat": 32.8099, "lng": -96.8294}
                    }
                }
            ],
            "status": "OK"
        }
        mock_get.return_value = mock_response
        
        # Call function
        result = geocode_address("1935 Medical District Dr, Dallas")
        
        # Verify results
        self.assertEqual(result["latitude"], 32.8099)
        self.assertEqual(result["longitude"], -96.8294)
        self.assertEqual(result["formatted_address"], "1935 Medical District Dr, Dallas, TX 75235, USA")
        
        # Verify API was called correctly
        mock_get.assert_called_once()
        self.assertIn("address=1935+Medical+District+Dr%2C+Dallas", mock_get.call_args[0][0])

    @patch('src.gui.hospital_search.requests.get')
    def test_geocode_address_no_results(self, mock_get):
        """Test geocoding when no results are found"""
        # Mock API response with no results
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [],
            "status": "ZERO_RESULTS"
        }
        mock_get.return_value = mock_response
        
        # Call function
        result = geocode_address("Invalid Address That Doesn't Exist")
        
        # Verify results
        self.assertIsNone(result)

    def test_format_hospital_results(self):
        """Test formatting of hospital search results for display"""
        # Test data
        hospitals = [
            {
                "name": "Children's Medical Center",
                "address": "1935 Medical District Dr, Dallas, TX 75235",
                "coordinates": {"lat": 32.8099, "lng": -96.8294},
                "facility_type": "Hospital",
                "services": ["pediatric_emergency", "pediatric_icu", "trauma_level_1"],
                "distance_miles": 15.3
            },
            {
                "name": "Medical City Dallas",
                "address": "7777 Forest Lane, Dallas, TX 75230",
                "coordinates": {"lat": 32.9112, "lng": -96.7665},
                "facility_type": "Hospital",
                "services": ["emergency", "trauma_level_2"],
                "distance_miles": 8.7
            }
        ]
        
        # Call function
        formatted = format_hospital_results(hospitals)
        
        # Verify formatting
        self.assertIn("Children's Medical Center", formatted)
        self.assertIn("1935 Medical District Dr", formatted)
        self.assertIn("15.3 miles", formatted)
        self.assertIn("Medical City Dallas", formatted)
        self.assertIn("8.7 miles", formatted)
        self.assertIn("Services", formatted)
        self.assertIn("pediatric_emergency", formatted)


if __name__ == "__main__":
    unittest.main()
