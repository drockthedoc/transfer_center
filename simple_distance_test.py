#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple test to verify distance calculations are working correctly.
"""

import logging
from src.core.models import Location
from src.utils.transport.distance import calculate_distance

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_distances():
    # Define hospital locations
    tch_main = Location(latitude=29.7096, longitude=-95.3987)  # Main campus
    tch_woodlands = Location(latitude=30.1757, longitude=-95.4629)  # Woodlands
    tch_west = Location(latitude=29.785, longitude=-95.7369)  # West Campus (Katy)
    tch_austin = Location(latitude=30.4743, longitude=-97.7905)  # North Austin
    tch_pavilion = Location(latitude=29.71, longitude=-95.4)  # Pavilion for Women
    
    # Test locations
    houston_location = Location(latitude=29.7604, longitude=-95.3698)  # Downtown Houston
    austin_location = Location(latitude=30.2672, longitude=-97.7431)  # Downtown Austin
    halfway_location = Location(latitude=30.0138, longitude=-96.5565)  # Roughly halfway
    
    # Print header
    print("\n" + "="*80)
    print("DISTANCE CALCULATION TEST")
    print("="*80)
    
    # Test case 1: Houston
    print("\nTEST CASE 1: Patient in HOUSTON")
    print("-" * 50)
    
    print("Distances from Houston:")
    distances_houston = [
        ("TCH Main Campus", calculate_distance(houston_location, tch_main)),
        ("TCH Woodlands", calculate_distance(houston_location, tch_woodlands)),
        ("TCH West Campus", calculate_distance(houston_location, tch_west)),
        ("TCH North Austin", calculate_distance(houston_location, tch_austin)),
        ("TCH Pavilion", calculate_distance(houston_location, tch_pavilion))
    ]
    
    # Sort by distance
    distances_houston.sort(key=lambda x: x[1])
    
    # Print sorted
    for name, dist in distances_houston:
        print(f"  {name}: {dist:.2f} km")
        
    # Identify closest
    closest_houston = distances_houston[0]
    print(f"\nCLOSEST TO HOUSTON: {closest_houston[0]} at {closest_houston[1]:.2f} km")
    
    # Test case 2: Austin
    print("\nTEST CASE 2: Patient in AUSTIN")
    print("-" * 50)
    
    print("Distances from Austin:")
    distances_austin = [
        ("TCH Main Campus", calculate_distance(austin_location, tch_main)),
        ("TCH Woodlands", calculate_distance(austin_location, tch_woodlands)),
        ("TCH West Campus", calculate_distance(austin_location, tch_west)),
        ("TCH North Austin", calculate_distance(austin_location, tch_austin)),
        ("TCH Pavilion", calculate_distance(austin_location, tch_pavilion))
    ]
    
    # Sort by distance
    distances_austin.sort(key=lambda x: x[1])
    
    # Print sorted
    for name, dist in distances_austin:
        print(f"  {name}: {dist:.2f} km")
        
    # Identify closest
    closest_austin = distances_austin[0]
    print(f"\nCLOSEST TO AUSTIN: {closest_austin[0]} at {closest_austin[1]:.2f} km")
    
    # Test case 3: Halfway
    print("\nTEST CASE 3: Patient HALFWAY between Houston and Austin")
    print("-" * 50)
    
    print("Distances from halfway point:")
    distances_halfway = [
        ("TCH Main Campus", calculate_distance(halfway_location, tch_main)),
        ("TCH Woodlands", calculate_distance(halfway_location, tch_woodlands)),
        ("TCH West Campus", calculate_distance(halfway_location, tch_west)),
        ("TCH North Austin", calculate_distance(halfway_location, tch_austin)),
        ("TCH Pavilion", calculate_distance(halfway_location, tch_pavilion))
    ]
    
    # Sort by distance
    distances_halfway.sort(key=lambda x: x[1])
    
    # Print sorted
    for name, dist in distances_halfway:
        print(f"  {name}: {dist:.2f} km")
        
    # Identify closest
    closest_halfway = distances_halfway[0]
    print(f"\nCLOSEST TO HALFWAY POINT: {closest_halfway[0]} at {closest_halfway[1]:.2f} km")
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"From HOUSTON: Closest is {closest_houston[0]}")
    print(f"From AUSTIN: Closest is {closest_austin[0]}")
    print(f"From HALFWAY: Closest is {closest_halfway[0]}")
    print("="*80)

if __name__ == "__main__":
    test_distances()
