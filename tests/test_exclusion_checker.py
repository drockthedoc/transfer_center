import unittest
from src.core.exclusion_checker import check_exclusions
from src.core.models import PatientData, HospitalCampus, CampusExclusion, Location, BedCensus, MetroArea

class TestPediatricExclusionChecker(unittest.TestCase): # Renamed class

    def setUp(self):
        # Pediatric Patient Examples
        self.patient_neonate = PatientData(
            patient_id="PED_NEO_01", 
            chief_complaint="Neonate, difficulty breathing", 
            clinical_history="Born at 30 weeks, needs NICU", 
            vital_signs={}, labs={}, 
            current_location=Location(latitude=0,longitude=0)
        )
        self.patient_child_cardiac = PatientData(
            patient_id="PED_CARD_01", 
            chief_complaint="5yo with palpitations, known complex congenital heart defect", 
            clinical_history="Scheduled for cardiac surgery consult", 
            vital_signs={}, labs={}, 
            current_location=Location(latitude=0,longitude=0)
        )
        self.patient_teen_no_issues = PatientData(
            patient_id="PED_TEEN_01", 
            chief_complaint="16yo with minor ankle sprain", 
            clinical_history="Healthy, active in sports", 
            vital_signs={}, labs={}, 
            current_location=Location(latitude=0,longitude=0)
        )

        # Pediatric-relevant Exclusions
        self.exclusion_no_neonatal_surgery = CampusExclusion(
            criteria_id="EX_NO_NEO_SURG", 
            criteria_name="No Neonatal Surgery", 
            description="This campus does not perform surgical interventions on neonates.", 
            affected_keywords_in_complaint=["neonate surgery", "newborn surgical repair"], 
            affected_keywords_in_history=["requires neonatal operation"]
        )
        self.exclusion_no_complex_cardiac_peds = CampusExclusion(
            criteria_id="EX_NO_PED_CARD_SURG", 
            criteria_name="No Pediatric Complex Cardiac Surgery", 
            description="Complex pediatric cardiac cases referred to specialized centers.", 
            affected_keywords_in_complaint=["complex heart defect surgery", "pediatric open heart"], 
            affected_keywords_in_history=["congenital heart defect repair needed"]
        )
        self.exclusion_adults_only_general = CampusExclusion( # An exclusion that a peds patient would NOT meet
            criteria_id="EX_ADULT_ONLY",
            criteria_name="Adults Only General Ward",
            description="This ward does not admit pediatric patients.",
            affected_keywords_in_complaint=["adult routine", "hypertension check adult"],
            affected_keywords_in_history=[]
        )
        
        # Campuses
        self.campus_specialized_peds = HospitalCampus(
            campus_id="TCH_MAIN_SIM", name="Peds Speciality Hospital", metro_area=MetroArea.HOUSTON, address="", location=Location(latitude=0,longitude=0),
            exclusions=[self.exclusion_no_neonatal_surgery, self.exclusion_no_complex_cardiac_peds, self.exclusion_adults_only_general],
            bed_census=BedCensus(total_beds=10, available_beds=1, icu_beds_total=1, icu_beds_available=1, nicu_beds_total=1, nicu_beds_available=1)
        )
        self.campus_general_no_peds_exclusions = HospitalCampus(
            campus_id="GEN_HOSP_SIM", name="General Hospital (No Peds Exclusions)", metro_area=MetroArea.AUSTIN, address="", location=Location(latitude=0,longitude=0),
            exclusions=[self.exclusion_adults_only_general], # Only has an adult exclusion
            bed_census=BedCensus(total_beds=10, available_beds=1, icu_beds_total=1, icu_beds_available=1, nicu_beds_total=1, nicu_beds_available=1)
        )

    def test_neonate_meets_no_neonatal_surgery_exclusion(self):
        # Update patient complaint to trigger exclusion
        self.patient_neonate.chief_complaint = "Neonate surgery needed for PDA ligation."
        met = check_exclusions(self.patient_neonate, self.campus_specialized_peds)
        self.assertEqual(len(met), 1)
        self.assertEqual(met[0].criteria_id, "EX_NO_NEO_SURG")
        self.patient_neonate.chief_complaint = "Neonate, difficulty breathing" # Reset

    def test_child_cardiac_meets_no_complex_cardiac_exclusion_history(self):
        # Update patient history to trigger exclusion
        self.patient_child_cardiac.clinical_history = "Patient has a congenital heart defect repair needed."
        met = check_exclusions(self.patient_child_cardiac, self.campus_specialized_peds)
        self.assertEqual(len(met), 1)
        self.assertEqual(met[0].criteria_id, "EX_NO_PED_CARD_SURG")
        self.patient_child_cardiac.clinical_history = "Scheduled for cardiac surgery consult" # Reset

    def test_teen_no_pediatric_exclusions_met(self):
        met = check_exclusions(self.patient_teen_no_issues, self.campus_specialized_peds)
        self.assertEqual(len(met), 0, "Teenager with minor issue should not meet these specific peds surgery exclusions.")

    def test_neonate_no_exclusions_at_general_hospital(self):
        # Neonate patient should not trigger the "Adults Only" exclusion at the general hospital
        met = check_exclusions(self.patient_neonate, self.campus_general_no_peds_exclusions)
        self.assertEqual(len(met), 0)

    def test_multiple_pediatric_exclusions_if_applicable(self):
        # Modify patient to trigger both exclusions hypothetically
        # This specific setup might be less realistic but tests the mechanism
        self.patient_child_cardiac.chief_complaint = "Neonate surgery for complex heart defect repair needed."
        self.patient_child_cardiac.clinical_history = "Also requires neonatal operation for other issue." 
        # Re-add affected_keywords_in_history for exclusion_no_neonatal_surgery for this test
        original_keywords_hist_neo_surg = self.exclusion_no_neonatal_surgery.affected_keywords_in_history
        self.exclusion_no_neonatal_surgery.affected_keywords_in_history = ["requires neonatal operation"]

        met = check_exclusions(self.patient_child_cardiac, self.campus_specialized_peds)
        self.assertEqual(len(met), 2)
        self.assertIn(self.exclusion_no_neonatal_surgery, met)
        self.assertIn(self.exclusion_no_complex_cardiac_peds, met)

        # Reset patient and exclusion for other tests
        self.patient_child_cardiac.chief_complaint = "5yo with palpitations, known complex congenital heart defect"
        self.patient_child_cardiac.clinical_history = "Scheduled for cardiac surgery consult"
        self.exclusion_no_neonatal_surgery.affected_keywords_in_history = original_keywords_hist_neo_surg


if __name__ == '__main__':
    unittest.main()
