import math
import unittest

from src.core.models import Location
from src.utils.geolocation import calculate_distance


class TestGeolocation(unittest.TestCase):

    def test_calculate_distance_zero(self):
        loc1 = Location(latitude=0.0, longitude=0.0)
        loc2 = Location(latitude=0.0, longitude=0.0)
        self.assertAlmostEqual(calculate_distance(loc1, loc2), 0.0, places=2)

    def test_calculate_distance_known_points(self):
        # Paris, France to London, UK (approximate coordinates)
        paris = Location(latitude=48.8566, longitude=2.3522)
        london = Location(latitude=51.5074, longitude=-0.1278)
        # Expected distance ~343-344 km via Haversine
        expected_distance_km = 343.5
        self.assertAlmostEqual(
            calculate_distance(paris, london), expected_distance_km, delta=2.0
        )

    def test_calculate_distance_north_south_pole(self):
        north_pole = Location(latitude=90.0, longitude=0.0)
        south_pole = Location(latitude=-90.0, longitude=0.0)
        # Expected distance is half the Earth's circumference through poles
        # Earth radius used in function is 6371 km. Circumference = 2 * pi * R.
        # Half = pi * R
        expected_distance_km = math.pi * 6371.0
        self.assertAlmostEqual(
            calculate_distance(north_pole, south_pole), expected_distance_km, delta=10.0
        )  # Delta for precision


if __name__ == "__main__":
    unittest.main()
