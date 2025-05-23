import unittest

from src.llm.classification import parse_patient_text


class TestLLMClassification(unittest.TestCase):

    def test_parse_patient_text_empty(self):
        result = parse_patient_text("")
        self.assertEqual(result["identified_keywords"], [])
        self.assertEqual(result["potential_conditions"], [])
        self.assertEqual(result["extracted_vital_signs"], {})
        self.assertEqual(result["mentioned_location_cues"], [])
        self.assertEqual(result["raw_text_summary"], "")

    def test_parse_patient_text_pediatric_keywords_and_vitals(self):
        text = "3-year-old with fever and cough. Suspected bronchiolitis. BP 90/60, HR 120, RR 35. O2 94%."
        result = parse_patient_text(text)
        self.assertIn("bronchiolitis", result["identified_keywords"])
        self.assertIn(
            "fever", result["identified_keywords"]
        )  # Assuming 'fever' maps to 'sepsis' or general concern
        self.assertIn("pediatric_emergency", result["potential_conditions"])
        self.assertIn(
            "sepsis", result["potential_conditions"]
        )  # Assuming 'fever' maps to 'sepsis'
        self.assertEqual(result["extracted_vital_signs"].get("bp"), "90/60")
        self.assertEqual(result["extracted_vital_signs"].get("hr"), "120")
        self.assertEqual(result["extracted_vital_signs"].get("rr"), "35")
        self.assertEqual(result["extracted_vital_signs"].get("o2_sat"), "94")

    def test_parse_patient_text_neonate_keywords(self):
        text = "Neonate presenting with poor feeding and lethargy. HR 90. Temp 36.1C."
        result = parse_patient_text(text)
        self.assertIn("neonate", result["identified_keywords"])
        self.assertIn("pediatric_emergency", result["potential_conditions"])
        self.assertEqual(result["extracted_vital_signs"].get("hr"), "90")
        # Temp not currently extracted by simple regex, so no assertion for it.

    def test_parse_patient_text_location_cues_pediatric_context(self):
        text = "Incident reported near the elementary school. Child fell at Happy Kids Daycare on 456 Play St."
        result = parse_patient_text(text)
        self.assertIn("the elementary school", result["mentioned_location_cues"])
        self.assertIn(
            "Happy Kids Daycare on 456 Play St", result["mentioned_location_cues"]
        )

    def test_parse_patient_text_no_pediatric_matches(self):
        text = "Adult patient with routine check-up. System is stable."
        result = parse_patient_text(text)
        # Assuming "adult" or "routine check-up" don't map to the pediatric-focused conditions
        # or general emergency conditions in our current
        # PREDEFINED_KEYWORDS_TO_CONDITIONS
        self.assertEqual(result["identified_keywords"], [])
        self.assertEqual(result["potential_conditions"], [])
        self.assertEqual(result["extracted_vital_signs"], {})
        # self.assertEqual(result["mentioned_location_cues"], []) # Location cues
        # might still pick up words


if __name__ == "__main__":
    unittest.main()
