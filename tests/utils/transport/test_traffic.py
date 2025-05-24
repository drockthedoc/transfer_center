#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for Traffic Analysis Module

This module tests the traffic analysis functionality for estimating travel times
based on traffic conditions.
"""

import unittest
from unittest.mock import patch, MagicMock
import datetime

from src.utils.transport.traffic import (
    get_traffic_conditions,
    estimate_travel_time_with_traffic,
    adjust_eta_for_traffic,
)


class TestTrafficAnalysis(unittest.TestCase):
    """Test cases for the traffic analysis functionality"""

    @patch('src.utils.transport.traffic.requests.get')
    def test_get_traffic_conditions(self, mock_get):
        """Test retrieval of traffic conditions between locations"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "routes": [
                {
                    "legs": [
                        {
                            "duration": {"value": 1800, "text": "30 mins"},
                            "duration_in_traffic": {"value": 2700, "text": "45 mins"},
                            "distance": {"value": 32000, "text": "32 km"}
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
        result = get_traffic_conditions(origin_lat, origin_lng, dest_lat, dest_lng)
        
        # Verify results
        self.assertEqual(result["base_duration_minutes"], 30)
        self.assertEqual(result["traffic_duration_minutes"], 45)
        self.assertEqual(result["traffic_factor"], 1.5)  # 45/30 = 1.5
        self.assertEqual(result["traffic_level"], "heavy")
        
        # Verify API was called correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args[0][0]
        self.assertIn("origins=32.7767,-96.797", call_args)
        self.assertIn("destinations=32.7555,-97.3308", call_args)
        self.assertIn("departure_time=now", call_args)

    @patch('src.utils.transport.traffic.requests.get')
    def test_get_traffic_conditions_moderate(self, mock_get):
        """Test retrieval of moderate traffic conditions"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "routes": [
                {
                    "legs": [
                        {
                            "duration": {"value": 1800, "text": "30 mins"},
                            "duration_in_traffic": {"value": 2160, "text": "36 mins"},
                            "distance": {"value": 32000, "text": "32 km"}
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Call function
        result = get_traffic_conditions(32.7767, -96.7970, 32.7555, -97.3308)
        
        # Verify results
        self.assertEqual(result["traffic_factor"], 1.2)  # 36/30 = 1.2
        self.assertEqual(result["traffic_level"], "moderate")

    @patch('src.utils.transport.traffic.requests.get')
    def test_get_traffic_conditions_light(self, mock_get):
        """Test retrieval of light traffic conditions"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "routes": [
                {
                    "legs": [
                        {
                            "duration": {"value": 1800, "text": "30 mins"},
                            "duration_in_traffic": {"value": 1920, "text": "32 mins"},
                            "distance": {"value": 32000, "text": "32 km"}
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Call function
        result = get_traffic_conditions(32.7767, -96.7970, 32.7555, -97.3308)
        
        # Verify results
        self.assertEqual(result["traffic_factor"], 1.07)  # 32/30 ≈ 1.07
        self.assertEqual(result["traffic_level"], "light")

    @patch('src.utils.transport.traffic.requests.get')
    def test_get_traffic_conditions_api_error(self, mock_get):
        """Test error handling when API returns an error"""
        # Mock API error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        # Call function
        result = get_traffic_conditions(32.7767, -96.7970, 32.7555, -97.3308)
        
        # Verify default values
        self.assertEqual(result["traffic_factor"], 1.0)
        self.assertEqual(result["traffic_level"], "unknown")
        self.assertTrue(result["estimated"])

    def test_estimate_travel_time_with_traffic(self):
        """Test estimation of travel time with traffic factors"""
        # Test with heavy traffic
        heavy_time = estimate_travel_time_with_traffic(
            base_time_minutes=30,
            traffic_level="heavy",
            time_of_day="rush_hour"
        )
        
        # Should be significantly increased (>= 1.4x)
        self.assertGreaterEqual(heavy_time, 42)
        
        # Test with moderate traffic
        moderate_time = estimate_travel_time_with_traffic(
            base_time_minutes=30,
            traffic_level="moderate",
            time_of_day="daytime"
        )
        
        # Should be moderately increased (1.2-1.4x)
        self.assertGreaterEqual(moderate_time, 36)
        self.assertLessEqual(moderate_time, 42)
        
        # Test with light traffic
        light_time = estimate_travel_time_with_traffic(
            base_time_minutes=30,
            traffic_level="light",
            time_of_day="night"
        )
        
        # Should be slightly increased (<= 1.2x)
        self.assertLessEqual(light_time, 36)
        self.assertGreaterEqual(light_time, 30)
        
        # Test with unknown traffic but rush hour
        unknown_rush = estimate_travel_time_with_traffic(
            base_time_minutes=30,
            traffic_level="unknown",
            time_of_day="rush_hour"
        )
        
        # Should use time of day as a fallback
        self.assertGreater(unknown_rush, 30)

    @patch('src.utils.transport.traffic.datetime')
    def test_adjust_eta_for_traffic(self, mock_datetime):
        """Test adjustment of ETA based on current time and traffic patterns"""
        # Mock current time as rush hour
        mock_now = datetime.datetime(2025, 5, 24, 17, 30)  # 5:30 PM
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.datetime.side_effect = lambda *args, **kw: datetime.datetime(*args, **kw)
        
        # Call function during rush hour
        rush_eta = adjust_eta_for_traffic(
            base_minutes=30,
            origin_lat=32.7767,
            origin_lng=-96.7970,
            dest_lat=32.7555,
            dest_lng=-97.3308,
            traffic_data={"traffic_level": "heavy", "traffic_factor": 1.5}
        )
        
        # Verify results
        self.assertEqual(rush_eta["adjusted_minutes"], 45)  # 30 * 1.5
        self.assertEqual(rush_eta["traffic_level"], "heavy")
        self.assertTrue(rush_eta["is_rush_hour"])
        
        # Mock current time as non-rush hour
        mock_now = datetime.datetime(2025, 5, 24, 10, 30)  # 10:30 AM
        mock_datetime.datetime.now.return_value = mock_now
        
        # Call function during non-rush hour
        normal_eta = adjust_eta_for_traffic(
            base_minutes=30,
            origin_lat=32.7767,
            origin_lng=-96.7970,
            dest_lat=32.7555,
            dest_lng=-97.3308,
            traffic_data={"traffic_level": "light", "traffic_factor": 1.1}
        )
        
        # Verify results
        self.assertEqual(normal_eta["adjusted_minutes"], 33)  # 30 * 1.1
        self.assertEqual(normal_eta["traffic_level"], "light")
        self.assertFalse(normal_eta["is_rush_hour"])


if __name__ == "__main__":
    unittest.main()
