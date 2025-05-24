#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for Transport Estimator Module

This module tests the transport estimator functionality which calculates
transport times for different modes of transportation.
"""

import unittest
from unittest.mock import patch, MagicMock

from src.utils.transport.estimator import (
    estimate_ground_transport_time,
    estimate_air_transport_time,
    compare_transport_options,
    calculate_mobilization_time,
)


class TestTransportEstimator(unittest.TestCase):
    """Test cases for the transport estimator functionality"""

    @patch('src.utils.transport.estimator.calculate_road_distance')
    @patch('src.utils.transport.estimator.get_traffic_conditions')
    def test_estimate_ground_transport_time(self, mock_traffic, mock_distance):
        """Test estimation of ground transport time"""
        # Mock distance calculation
        mock_distance.return_value = {
            "distance_miles": 40,
            "duration_minutes": 45,
            "estimated": False
        }
        
        # Mock traffic conditions
        mock_traffic.return_value = {
            "traffic_level": "moderate",
            "traffic_factor": 1.2,
            "estimated": False
        }
        
        # Call function
        result = estimate_ground_transport_time(
            origin_lat=32.7767, origin_lng=-96.7970,
            dest_lat=32.7555, dest_lng=-97.3308,
            transport_type="ambulance"
        )
        
        # Verify results
        self.assertEqual(result["base_time_minutes"], 45)
        self.assertEqual(result["adjusted_time_minutes"], 54)  # 45 * 1.2
        self.assertEqual(result["distance_miles"], 40)
        self.assertEqual(result["traffic_level"], "moderate")
        
        # Verify mocks were called
        mock_distance.assert_called_once()
        mock_traffic.assert_called_once()
        
        # Test with expedited transport
        expedited_result = estimate_ground_transport_time(
            origin_lat=32.7767, origin_lng=-96.7970,
            dest_lat=32.7555, dest_lng=-97.3308,
            transport_type="ambulance",
            emergency=True
        )
        
        # Should be faster than non-emergency
        self.assertLess(expedited_result["adjusted_time_minutes"], 54)

    @patch('src.utils.transport.estimator.calculate_straight_line_distance')
    def test_estimate_air_transport_time(self, mock_distance):
        """Test estimation of air transport time"""
        # Mock distance calculation
        mock_distance.return_value = 40  # 40 miles
        
        # Call function for helicopter
        helicopter_result = estimate_air_transport_time(
            origin_lat=32.7767, origin_lng=-96.7970,
            dest_lat=32.7555, dest_lng=-97.3308,
            aircraft_type="helicopter"
        )
        
        # Verify results
        self.assertEqual(helicopter_result["distance_miles"], 40)
        # Typical helicopter cruising speed is ~150 mph
        self.assertAlmostEqual(helicopter_result["flight_time_minutes"], 16, delta=2)
        self.assertIn("total_time_minutes", helicopter_result)
        self.assertGreater(helicopter_result["total_time_minutes"], 
                          helicopter_result["flight_time_minutes"])
        
        # Call function for fixed-wing
        fixed_wing_result = estimate_air_transport_time(
            origin_lat=32.7767, origin_lng=-96.7970,
            dest_lat=32.7555, dest_lng=-97.3308,
            aircraft_type="fixed_wing"
        )
        
        # Fixed-wing should be faster in the air but might have longer total time
        self.assertLess(fixed_wing_result["flight_time_minutes"], 
                        helicopter_result["flight_time_minutes"])

    @patch('src.utils.transport.estimator.estimate_ground_transport_time')
    @patch('src.utils.transport.estimator.estimate_air_transport_time')
    def test_compare_transport_options(self, mock_air, mock_ground):
        """Test comparison of different transport options"""
        # Mock ground transport
        mock_ground.return_value = {
            "adjusted_time_minutes": 55,
            "distance_miles": 40,
            "traffic_level": "moderate",
            "total_time_minutes": 70  # Including mobilization
        }
        
        # Mock air transport
        mock_air.return_value = {
            "flight_time_minutes": 15,
            "distance_miles": 40,
            "total_time_minutes": 45  # Including mobilization
        }
        
        # Call function
        result = compare_transport_options(
            origin_lat=32.7767, origin_lng=-96.7970,
            dest_lat=32.7555, dest_lng=-97.3308,
            patient_condition="critical"
        )
        
        # Verify results
        self.assertEqual(result["fastest_method"], "helicopter")
        self.assertEqual(result["helicopter"]["total_time_minutes"], 45)
        self.assertEqual(result["ground_ambulance"]["total_time_minutes"], 70)
        self.assertGreater(result["time_saved_minutes"], 20)
        
        # For critical patients, should recommend helicopter
        self.assertEqual(result["recommended_transport"], "helicopter")
        
        # Test with less critical patient and smaller difference
        mock_ground.return_value["total_time_minutes"] = 50  # Only 5 min difference
        
        stable_result = compare_transport_options(
            origin_lat=32.7767, origin_lng=-96.7970,
            dest_lat=32.7555, dest_lng=-97.3308,
            patient_condition="stable"
        )
        
        # For stable patients with small time difference, should recommend ground
        self.assertEqual(stable_result["recommended_transport"], "ground_ambulance")

    def test_calculate_mobilization_time(self):
        """Test calculation of mobilization time for different transport types"""
        # Test helicopter mobilization
        helicopter_time = calculate_mobilization_time(
            transport_type="helicopter",
            day_time=True,
            weather_conditions="clear"
        )
        
        # Typical helicopter mobilization is 10-15 minutes
        self.assertGreaterEqual(helicopter_time, 10)
        self.assertLessEqual(helicopter_time, 15)
        
        # Test helicopter at night or bad weather (should be longer)
        night_helicopter = calculate_mobilization_time(
            transport_type="helicopter",
            day_time=False,
            weather_conditions="clear"
        )
        
        bad_weather_helicopter = calculate_mobilization_time(
            transport_type="helicopter",
            day_time=True,
            weather_conditions="stormy"
        )
        
        self.assertGreater(night_helicopter, helicopter_time)
        self.assertGreater(bad_weather_helicopter, helicopter_time)
        
        # Test ground ambulance
        ambulance_time = calculate_mobilization_time(
            transport_type="ground_ambulance",
            day_time=True,
            weather_conditions="clear"
        )
        
        # Typical ambulance mobilization is 5-10 minutes
        self.assertGreaterEqual(ambulance_time, 5)
        self.assertLessEqual(ambulance_time, 10)


if __name__ == "__main__":
    unittest.main()
