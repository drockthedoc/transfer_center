import unittest
from unittest.mock import patch, MagicMock
import requests # Required for requests.exceptions.Timeout
from src.utils.travel_calculator import get_road_travel_info, get_air_travel_info
from src.core.models import Location, WeatherData

class TestTravelCalculator(unittest.TestCase):

    def setUp(self):
        self.loc1 = Location(latitude=0.0, longitude=0.0)
        self.loc2 = Location(latitude=1.0, longitude=1.0) # Approx 157 km apart

    @patch('src.utils.travel_calculator.requests.get')
    def test_get_road_travel_info_osrm_success(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'routes': [{'distance': 157000, 'duration': 5400}] # 157km, 90 mins (5400s)
        }
        mock_requests_get.return_value = mock_response

        result = get_road_travel_info(self.loc1, self.loc2)
        self.assertEqual(result["source"], "OSRM API")
        self.assertAlmostEqual(result["distance_km"], 157.0)
        self.assertAlmostEqual(result["time_minutes"], 90.0)

    @patch('src.utils.travel_calculator.requests.get')
    def test_get_road_travel_info_osrm_no_route(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'code': 'NoRoute', 'routes': []} # OSRM no route response
        mock_requests_get.return_value = mock_response
        
        result = get_road_travel_info(self.loc1, self.loc2)
        self.assertEqual(result["source"], "Fallback Haversine/Average Speed")
        # Check if distance is roughly Haversine for loc1 and loc2 (approx 157 km)
        self.assertAlmostEqual(result["distance_km"], 157.24, delta=0.1) 

    @patch('src.utils.travel_calculator.requests.get')
    def test_get_road_travel_info_osrm_api_failure(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.Timeout # Simulate timeout

        result = get_road_travel_info(self.loc1, self.loc2)
        self.assertEqual(result["source"], "Fallback Haversine/Average Speed")
        self.assertAlmostEqual(result["distance_km"], 157.24, delta=0.1)

    def test_get_air_travel_info_viable(self):
        weather = WeatherData(temperature_celsius=20, wind_speed_kph=10, precipitation_mm_hr=0, visibility_km=10, adverse_conditions=[])
        result = get_air_travel_info(self.loc1, self.loc2, weather)
        self.assertTrue(result["viable"])
        self.assertAlmostEqual(result["distance_km"], 157.24, delta=0.1)
        # Time = (157.24 / 240)*60 + 20 (fixed_maneuver_time) approx 39.3 + 20 = 59.3 mins
        self.assertAlmostEqual(result["time_minutes"], 59.31, delta=0.1)


    def test_get_air_travel_info_non_viable_adverse_conditions(self):
        weather = WeatherData(temperature_celsius=20, wind_speed_kph=10, precipitation_mm_hr=0, visibility_km=10, adverse_conditions=["FOG"])
        result = get_air_travel_info(self.loc1, self.loc2, weather)
        self.assertFalse(result["viable"])
        # The reason string in travel_calculator.py is "Adverse weather: {condition}."
        self.assertIn("Adverse weather: FOG", result["reason"])

    def test_get_air_travel_info_non_viable_visibility(self):
        # MIN_VISIBILITY_KM_VFR = 1.5 in travel_calculator
        weather = WeatherData(temperature_celsius=20, wind_speed_kph=10, precipitation_mm_hr=0, visibility_km=1.0, adverse_conditions=[])
        result = get_air_travel_info(self.loc1, self.loc2, weather)
        self.assertFalse(result["viable"])
        # The reason string in travel_calculator.py is "Visibility {weather.visibility_km}km < minimum {MIN_VISIBILITY_KM_VFR}km for VFR."
        self.assertIn("Visibility 1.0km < minimum 1.5km for VFR.", result["reason"])

    def test_get_air_travel_info_non_viable_wind_speed(self):
        # MAX_WIND_SPEED_KPH_AIR = 70.0 in travel_calculator
        weather = WeatherData(temperature_celsius=20, wind_speed_kph=75, precipitation_mm_hr=0, visibility_km=10, adverse_conditions=[])
        result = get_air_travel_info(self.loc1, self.loc2, weather)
        self.assertFalse(result["viable"])
        # The reason string in travel_calculator.py is "Wind speed {weather.wind_speed_kph}kph > maximum {MAX_WIND_SPEED_KPH_AIR}kph."
        self.assertIn("Wind speed 75.0kph > maximum 70.0kph.", result["reason"])

    def test_get_air_travel_info_zero_speed(self):
        weather = WeatherData(temperature_celsius=20, wind_speed_kph=10, precipitation_mm_hr=0, visibility_km=10, adverse_conditions=[])
        result = get_air_travel_info(self.loc1, self.loc2, weather, average_helicopter_speed_kmh=0)
        self.assertFalse(result["viable"])
        # The reason string in travel_calculator.py is "Average helicopter speed must be positive."
        self.assertIn("Average helicopter speed must be positive.", result["reason"])

if __name__ == '__main__':
    unittest.main()
