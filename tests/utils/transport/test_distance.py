#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for Distance Calculator Module

This module tests the distance calculation functionality for determining
straight-line and road distances between coordinates.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.utils.transport.distance import (
    calculate_straight_line_distance,
    calculate_road_distance,
    calculate_distance_matrix,
)


class TestDistanceCalculator(unittest.TestCase):
    """Test cases for the distance calculator functionality"""

    def test_calculate_straight_line_distance(self):
        """Test calculation of straight-line (haversine) distance between coordinates"""
        # Test with known coordinates
        # Dallas to Fort Worth coordinates (approx)
        dallas_lat, dallas_lng = 32.7767, -96.7970
        fort_worth_lat, fort_worth_lng = 32.7555, -97.3308
        
        distance = calculate_straight_line_distance(
            dallas_lat, dallas_lng, fort_worth_lat, fort_worth_lng
        )
        
        # Should be approximately 30 miles
        self.assertGreater(distance, 29)
        self.assertLess(distance, 33)
        
        # Test with same coordinates (should be 0)
        same_point = calculate_straight_line_distance(
            dallas_lat, dallas_lng, dallas_lat, dallas_lng
        )
        
        self.assertAlmostEqual(same_point, 0, delta=0.1)
        
        # Test with coordinates at opposite sides of Earth
        antipodal = calculate_straight_line_distance(
            90, 0, -90, 0  # North pole to South pole
        )
        
        # Should be approximately 12,430 miles (Earth's diameter / 2 * pi)
        self.assertGreater(antipodal, 12000)
        self.assertLess(antipodal, 12500)

    @patch('src.utils.transport.distance.requests.get')
    def test_calculate_road_distance(self, mock_get):
        """Test calculation of road distance between coordinates using API"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "routes": [
                {
                    "legs": [
                        {
                            "distance": {"value": 48500, "text": "48.5 km"},
                            "duration": {"value": 2700, "text": "45 mins"}
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Test coordinates
        origin_lat, origin_lng = 32.7767, -96.7970  # Dallas
        dest_lat, dest_lng = 32.7555, -97.3308  # Fort Worth
        
        # Call function
        result = calculate_road_distance(
            origin_lat, origin_lng, dest_lat, dest_lng
        )
        
        # Verify results (convert km to miles)
        self.assertAlmostEqual(result["distance_miles"], 30.1, delta=0.1)
        self.assertEqual(result["duration_minutes"], 45)
        
        # Verify API was called correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args[0][0]
        self.assertIn("origins=32.7767,-96.797", call_args)
        self.assertIn("destinations=32.7555,-97.3308", call_args)

    @patch('src.utils.transport.distance.requests.get')
    def test_calculate_road_distance_api_error(self, mock_get):
        """Test error handling when API returns an error"""
        # Mock API error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        # Test coordinates
        origin_lat, origin_lng = 32.7767, -96.7970
        dest_lat, dest_lng = 32.7555, -97.3308
        
        # Call function
        result = calculate_road_distance(
            origin_lat, origin_lng, dest_lat, dest_lng
        )
        
        # Verify fallback to straight-line distance
        self.assertIn("distance_miles", result)
        self.assertIn("duration_minutes", result)
        self.assertIn("estimated", result)
        self.assertTrue(result["estimated"])

    @patch('src.utils.transport.distance.requests.get')
    def test_calculate_distance_matrix(self, mock_get):
        """Test calculation of distance matrix between multiple origins and destinations"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "rows": [
                {
                    "elements": [
                        {
                            "distance": {"value": 48500, "text": "48.5 km"},
                            "duration": {"value": 2700, "text": "45 mins"},
                            "status": "OK"
                        },
                        {
                            "distance": {"value": 24100, "text": "24.1 km"},
                            "duration": {"value": 1500, "text": "25 mins"},
                            "status": "OK"
                        }
                    ]
                },
                {
                    "elements": [
                        {
                            "distance": {"value": 35700, "text": "35.7 km"},
                            "duration": {"value": 2100, "text": "35 mins"},
                            "status": "OK"
                        },
                        {
                            "distance": {"value": 12900, "text": "12.9 km"},
                            "duration": {"value": 900, "text": "15 mins"},
                            "status": "OK"
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Test data
        origins = [
            {"lat": 32.7767, "lng": -96.7970},  # Dallas
            {"lat": 33.0784, "lng": -96.8084}   # Plano
        ]
        
        destinations = [
            {"lat": 32.7555, "lng": -97.3308},  # Fort Worth
            {"lat": 32.9342, "lng": -96.8347}   # Addison
        ]
        
        # Call function
        result = calculate_distance_matrix(origins, destinations)
        
        # Verify results
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), 2)
        self.assertAlmostEqual(result[0][0]["distance_miles"], 30.1, delta=0.1)
        self.assertEqual(result[0][0]["duration_minutes"], 45)
        self.assertAlmostEqual(result[1][1]["distance_miles"], 8.0, delta=0.1)
        self.assertEqual(result[1][1]["duration_minutes"], 15)
        
        # Verify API was called correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args[0][0]
        self.assertIn("origins=", call_args)
        self.assertIn("destinations=", call_args)


if __name__ == "__main__":
    unittest.main()
