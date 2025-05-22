import unittest
from unittest.mock import patch, MagicMock
from src.core.decision_engine import recommend_campus
from src.core.models import (
    PatientData, HospitalCampus, BedCensus, Location, CampusExclusion, 
    WeatherData, TransferRequest, MetroArea, TransportMode, HelipadData, Recommendation
)

class TestDecisionEngine(unittest.TestCase):

    def setUp(self):
        # Pediatric Patient Examples
        self.patient_picu_candidate = PatientData(
            patient_id="PED_PICU01", 
            chief_complaint="3yo with severe respiratory distress, wheezing, RR 50, O2 85%", 
            clinical_history="Hx of asthma", 
            vital_signs={"rr": "50", "o2_sat": "85%"}, 
            labs={}, 
            current_location=Location(latitude=29.7000, longitude=-95.4000) # Patient's location
        )
        self.patient_nicu_candidate = PatientData(
            patient_id="PED_NICU01", 
            chief_complaint="Neonate, 1 day old, apneic episodes, bradycardia", 
            clinical_history="Born at 32 weeks", 
            vital_signs={"hr": "60"}, 
            labs={}, 
            current_location=Location(latitude=30.2000, longitude=-95.5000)
        )
        self.patient_general_pediatric = PatientData(
            patient_id="PED_GEN01",
            chief_complaint="5yo with fever and sore throat",
            clinical_history="NKA",
            vital_signs={"temp_c": "39.5"}, labs={},
            current_location=Location(latitude=29.8000, longitude=-95.6000)
        )

        # TCH Campus Examples (Simplified from new sample data)
        self.tch_main = HospitalCampus(
            campus_id="TCH_MAIN_TMC", name="TCH Main (TMC)", metro_area=MetroArea.HOUSTON, 
            address="6621 Fannin St, Houston, TX 77030", location=Location(latitude=29.7096, longitude=-95.3987),
            exclusions=[
                CampusExclusion(criteria_id="TCHM_EX01", criteria_name="No Adult Primary Care", description="", affected_keywords_in_complaint=[], affected_keywords_in_history=["adult patient general care"])
            ], 
            bed_census=BedCensus(total_beds=973, available_beds=80, icu_beds_total=120, icu_beds_available=15, nicu_beds_total=150, nicu_beds_available=20),
            helipads=[HelipadData(helipad_id="TCH_MAIN_HELI", location=Location(latitude=29.7090, longitude=-95.3985))]
        )
        self.tch_woodlands = HospitalCampus(
            campus_id="TCH_WOODLANDS", name="TCH Woodlands", metro_area=MetroArea.HOUSTON, 
            address="17600 I-45 South, The Woodlands, TX 77384", location=Location(latitude=30.1757, longitude=-95.4629),
            exclusions=[
                CampusExclusion(criteria_id="TCHW_EX01", criteria_name="No Solid Organ Transplant Surgery", description="", affected_keywords_in_complaint=["transplant surgery needed"], affected_keywords_in_history=[])
            ],
            bed_census=BedCensus(total_beds=200, available_beds=25, icu_beds_total=30, icu_beds_available=5, nicu_beds_total=40, nicu_beds_available=8),
            helipads=[HelipadData(helipad_id="TCH_WOOD_HELI", location=Location(latitude=30.1755, longitude=-95.4627))]
        )
        self.tch_west_katy = HospitalCampus( # Campus with PICU but no NICU beds available for a specific test
            campus_id="TCH_WEST_KATY", name="TCH West Campus (Katy)", metro_area=MetroArea.HOUSTON,
            address="18200 Katy Fwy, Houston, TX 77094", location=Location(latitude=29.7850, longitude=-95.7369),
            exclusions=[
                CampusExclusion(criteria_id="TCHWC_EX02", criteria_name="NICU Level III (No Level IV)", description="", affected_keywords_in_complaint=["micropremie"], affected_keywords_in_history=[])
            ],
            bed_census=BedCensus(total_beds=150, available_beds=20, icu_beds_total=22, icu_beds_available=4, nicu_beds_total=30, nicu_beds_available=0), # No NICU beds available
            helipads=[HelipadData(helipad_id="TCH_WEST_HELI", location=Location(latitude=29.7848, longitude=-95.7367))]
        )
        self.tch_austin_north = HospitalCampus( # Campus with NICU but no PICU beds available
            campus_id="TCH_NORTH_AUSTIN", name="TCH North Austin (Rep.)", metro_area=MetroArea.AUSTIN_METRO,
            address="123 Childrens Way, Austin, TX 78759", location=Location(latitude=30.4581, longitude=-97.7946),
            exclusions=[],
            bed_census=BedCensus(total_beds=100, available_beds=15, icu_beds_total=15, icu_beds_available=0, nicu_beds_total=20, nicu_beds_available=5), # No PICU beds
            helipads=[HelipadData(helipad_id="TCH_NAUS_HELI", location=Location(latitude=30.4579, longitude=-97.7944))]
        )

        self.all_campuses = [self.tch_main, self.tch_woodlands, self.tch_west_katy, self.tch_austin_north]
        self.weather_good = WeatherData(temperature_celsius=20, wind_speed_kph=10, precipitation_mm_hr=0, visibility_km=10, adverse_conditions=[])
        self.sending_location_houston_med_center_prox = Location(latitude=29.71, longitude=-95.40) # Near TCH Main
        self.transport_modes = [TransportMode.GROUND_AMBULANCE, TransportMode.AIR_AMBULANCE]


    @patch('src.core.decision_engine.parse_patient_text')
    @patch('src.core.decision_engine.check_exclusions')
    @patch('src.core.decision_engine.get_road_travel_info')
    @patch('src.core.decision_engine.get_air_travel_info')
    @patch('src.core.decision_engine.generate_simple_explanation')
    def test_recommendation_picu_patient_chooses_tch_main_by_air(
        self, mock_generate_explanation, mock_get_air_travel, mock_get_road_travel, 
        mock_check_exclusions, mock_parse_patient_text
    ):
        mock_parse_patient_text.return_value = {"potential_conditions": ["respiratory", "pediatric_emergency"], "extracted_vital_signs": {}, "identified_keywords": [], "mentioned_location_cues": [], "raw_text_summary":""} # Indicates PICU need
        mock_check_exclusions.return_value = [] 
        mock_generate_explanation.return_value = {"summary": "Mocked explanation"}

        def road_travel_side_effect(origin, dest_campus_loc):
            if dest_campus_loc.latitude == self.tch_main.location.latitude: return {"time_minutes": 30, "distance_km": 5, "source": "Mocked Road"}
            if dest_campus_loc.latitude == self.tch_woodlands.location.latitude: return {"time_minutes": 60, "distance_km": 50, "source": "Mocked Road"}
            # Add others if needed for specific scenarios, or a default
            return {"time_minutes": 120, "distance_km": 100, "source": "Mocked Road Default"}
        mock_get_road_travel.side_effect = road_travel_side_effect
        
        def air_travel_side_effect(origin, dest_helipad_loc, weather):
            if dest_helipad_loc.latitude == self.tch_main.helipads[0].location.latitude: return {"viable": True, "time_minutes": 10, "distance_km": 5, "reason": "Mocked Air Viable for TCH Main"}
            if dest_helipad_loc.latitude == self.tch_woodlands.helipads[0].location.latitude: return {"viable": True, "time_minutes": 25, "distance_km": 50, "reason": "Mocked Air Viable for TCH Woodlands"}
            return {"viable": False, "time_minutes": float('inf'), "distance_km": float('inf'), "reason": "Mocked Air Non-Viable"}
        mock_get_air_travel.side_effect = air_travel_side_effect

        request = TransferRequest(
            request_id="R_PICU_001", patient_data=self.patient_picu_candidate, 
            sending_facility_name="Sending Clinic Houston", sending_facility_location=self.sending_location_houston_med_center_prox,
        )
        recommendation = recommend_campus(request, [self.tch_main, self.tch_woodlands], self.weather_good, self.transport_modes)

        self.assertIsNotNone(recommendation)
        self.assertEqual(recommendation.recommended_campus_id, "TCH_MAIN_TMC")
        
        # Check if air transport was chosen for TCH Main
        # The notes for the chosen campus are in recommendation.notes
        chosen_campus_notes_text = " ".join(recommendation.notes) if recommendation.notes else ""
        self.assertIn("Chosen Transport: Air", chosen_campus_notes_text, "Air transport should have been chosen for TCH Main.")
        self.assertIn("Est. Time: 10 min", chosen_campus_notes_text, "Air transport time for TCH Main should be 10 min.")
        mock_generate_explanation.assert_called_once()


    @patch('src.core.decision_engine.parse_patient_text')
    @patch('src.core.decision_engine.check_exclusions')
    @patch('src.core.decision_engine.get_road_travel_info')
    @patch('src.core.decision_engine.get_air_travel_info')
    @patch('src.core.decision_engine.generate_simple_explanation')
    def test_recommendation_nicu_patient_chooses_tch_woodlands(
        self, mock_generate_explanation, mock_get_air_travel, mock_get_road_travel, 
        mock_check_exclusions, mock_parse_patient_text
    ):
        # Patient needs NICU. TCH Main has NICU, TCH Woodlands has NICU. TCH West has 0 NICU beds available.
        mock_parse_patient_text.return_value = {"potential_conditions": ["pediatric_emergency", "neonate_sepsis"], "raw_text_summary":""} # Indicates NICU
        mock_check_exclusions.return_value = []
        mock_generate_explanation.return_value = {"summary": "Mocked explanation"}

        # Mock travel: Make Woodlands slightly more favorable or Main unavailable for NICU for some reason to test selection
        def road_travel_side_effect(origin, dest_campus_loc):
            if dest_campus_loc.latitude == self.tch_main.location.latitude: return {"time_minutes": 30, "distance_km": 20, "source": "Mocked Road"}
            if dest_campus_loc.latitude == self.tch_woodlands.location.latitude: return {"time_minutes": 25, "distance_km": 15, "source": "Mocked Road"} # Woodlands closer/faster by road
            if dest_campus_loc.latitude == self.tch_west_katy.location.latitude: return {"time_minutes": 40, "distance_km": 30, "source": "Mocked Road"}
            return {"time_minutes": 120, "distance_km": 100, "source": "Mocked Road Default"}
        mock_get_road_travel.side_effect = road_travel_side_effect
        
        def air_travel_side_effect(origin, dest_helipad_loc, weather):
            # Air travel to Main is not viable or much slower for this NICU scenario
            if dest_helipad_loc.latitude == self.tch_main.helipads[0].location.latitude: return {"viable": False, "reason":"Mocked Air Non-Viable for Main", "time_minutes": float('inf')}
            if dest_helipad_loc.latitude == self.tch_woodlands.helipads[0].location.latitude: return {"viable": True, "time_minutes": 15, "distance_km": 15, "reason": "Mocked Air Viable for Woodlands"}
            # TCH West has helipad, but no NICU beds, so it should be filtered by beds.
            if dest_helipad_loc.latitude == self.tch_west_katy.helipads[0].location.latitude: return {"viable": True, "time_minutes": 20, "distance_km": 25, "reason": "Mocked Air Viable for West"}
            return {"viable": False, "time_minutes": float('inf'), "distance_km": float('inf'), "reason": "Mocked Air Non-Viable"}
        mock_get_air_travel.side_effect = air_travel_side_effect
        
        # Campuses for this test: TCH Main (NICU), TCH Woodlands (NICU), TCH West (No NICU beds)
        test_campuses = [self.tch_main, self.tch_woodlands, self.tch_west_katy]

        request = TransferRequest(
            request_id="R_NICU_001", patient_data=self.patient_nicu_candidate, 
            sending_facility_name="Sending Clinic North", sending_facility_location=Location(latitude=30.0, longitude=-95.4), # Closer to Woodlands
        )
        recommendation = recommend_campus(request, test_campuses, self.weather_good, self.transport_modes)

        self.assertIsNotNone(recommendation)
        self.assertEqual(recommendation.recommended_campus_id, "TCH_WOODLANDS") # Woodlands chosen due to travel/air viability
        chosen_campus_notes_text = " ".join(recommendation.notes) if recommendation.notes else ""
        self.assertIn("Chosen Transport: Air", chosen_campus_notes_text) # Air to Woodlands
        self.assertIn("Est. Time: 15 min", chosen_campus_notes_text)


    @patch('src.core.decision_engine.parse_patient_text')
    @patch('src.core.decision_engine.check_exclusions')
    @patch('src.core.decision_engine.get_road_travel_info')
    @patch('src.core.decision_engine.get_air_travel_info')
    @patch('src.core.decision_engine.generate_simple_explanation')
    def test_exclusion_prevents_recommendation(
        self, mock_generate_explanation, mock_get_air_travel, mock_get_road_travel, 
        mock_check_exclusions, mock_parse_patient_text
    ):
        mock_parse_patient_text.return_value = {"potential_conditions": ["pediatric_emergency"], "raw_text_summary":""} # General peds
        mock_generate_explanation.return_value = {"summary": "Mocked explanation"}
        
        # TCH Main is the only campus, but it will be excluded.
        # The exclusion in TCH Main is "No Adult Primary Care" with keyword "adult patient general care" in history.
        # Let's make our pediatric patient's history trigger this for testing exclusion logic.
        self.patient_general_pediatric.clinical_history = "This is an adult patient general care record for a child." 
        
        mock_check_exclusions.side_effect = lambda patient, campus: [self.tch_main.exclusions[0]] if campus.campus_id == "TCH_MAIN_TMC" and "adult patient general care" in patient.clinical_history else []

        mock_get_road_travel.return_value = {"time_minutes": 30, "distance_km": 20, "source": "Mocked Road"}
        mock_get_air_travel.return_value = {"viable": True, "time_minutes": 15, "distance_km": 15, "reason": "Mocked Air Viable"}

        request = TransferRequest(
            request_id="R_EXCL_001", patient_data=self.patient_general_pediatric, 
            sending_facility_name="Sending Clinic", sending_facility_location=self.sending_location_houston_med_center_prox,
        )
        recommendation = recommend_campus(request, [self.tch_main], self.weather_good, self.transport_modes)
        
        self.assertIsNone(recommendation, "Recommendation should be None as the only campus is excluded.")


if __name__ == '__main__':
    unittest.main()
