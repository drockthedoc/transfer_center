"""
Specialty assessment component for LLM integration.

This module handles the assessment of specialty needs based on extracted clinical entities.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from src.llm.utils import robust_json_parser

logger = logging.getLogger(__name__)


class SpecialtyAssessor:
    """Handles assessment of specialty needs based on extracted clinical entities."""

    def __init__(self, client, model: str):
        """
        Initialize the specialty assessor.

        Args:
            client: OpenAI client instance
            model: Name of the model to use
        """
        self.client = client
        self.model = model

    def assess_specialties(
        self,
        extracted_entities: Dict[str, Any],
        scoring_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Assess specialty needs based on extracted clinical entities and scoring results.

        Args:
            extracted_entities: Dictionary of extracted clinical entities
            scoring_results: Optional dictionary containing pediatric scoring system results

        Returns:
            Dictionary with specialty need assessment
        """
        logger.info("Running specialty assessment...")

        # Construct the prompt for specialty assessment
        prompt = self._build_assessment_prompt(extracted_entities, scoring_results)

        try:
            # Call the LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a pediatric medical specialist with expertise in severity assessment and care level determination.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Slight variation allowed
                max_tokens=1500,
            )

            # Extract JSON response
            content = response.choices[0].message.content
            logger.debug(f"Specialty assessment raw response: {content}")

            # Parse JSON from response using the robust parser
            assessment = robust_json_parser(content)

            if assessment:
                logger.info("Specialty assessment successful using robust parser")
                return assessment
            else:
                logger.warning(
                    "Robust JSON parsing failed, falling back to rule-based assessment"
                )
                # Fallback to simple assessment
                return self._fallback_assessment(extracted_entities)

        except Exception as e:
            logger.error(f"Error during specialty assessment: {e}")
            return self._fallback_assessment(extracted_entities)

    def _build_assessment_prompt(
        self,
        extracted_entities: Dict[str, Any],
        scoring_results: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build the prompt for specialty assessment.

        Args:
            extracted_entities: Dictionary of extracted clinical entities
            scoring_results: Optional dictionary containing pediatric scoring system results

        Returns:
            Formatted prompt string
        """
        # Format the extracted entities as a clean string
        entities_str = json.dumps(extracted_entities, indent=2)

        # Build the base prompt
        prompt = f"""Based on the following extracted clinical information, assess which medical specialties would be required for this patient:

{entities_str}
"""

        # Add scoring results if available
        if scoring_results and isinstance(scoring_results, dict):
            # Format the scoring results nicely
            scores_str = json.dumps(scoring_results, indent=2)
            prompt += f"""

The patient has been evaluated using the following pediatric scoring systems, which provide objective assessments of severity:

{scores_str}

These scores should be considered when determining appropriate care levels and specialties required.
"""

        # Complete the prompt with output instructions
        prompt += f"""

Provide the following in JSON format:
1. A list of required medical specialties ranked by importance (e.g., "Cardiology", "Pulmonology")
2. Recommended level of care ("General", "ICU", "PICU", or "NICU")
3. A brief clinical reasoning for each specialty and care level recommendation that references specific clinical findings and scoring results if available
4. A list of medical conditions or diagnoses that can be inferred from the information

JSON Output:
```json
{{
  "required_specialties": [
    {{
      "specialty": "Specialty name",
      "importance": "primary/secondary/consult",
      "reasoning": "Brief explanation"
    }}
  ],
  "recommended_care_level": "Care level",
  "care_level_reasoning": "Explanation for care level recommendation that references scoring results if available",
  "potential_conditions": ["Condition 1", "Condition 2"],
  "clinical_summary": "Brief summary of case, severity scores, and recommendations"
}}
```

Respond only with the JSON output.
"""

        return prompt

    def _fallback_assessment(
        self, extracted_entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fallback assessment method using rule-based approach.

        Args:
            extracted_entities: Dictionary of extracted clinical entities

        Returns:
            Dictionary with specialty need assessment
        """
        # Initialize result
        result = {
            "required_specialties": [],
            "recommended_care_level": "General",
            "care_level_reasoning": "Based on limited available information",
            "potential_conditions": [],
            "clinical_summary": "Assessment based on rule-based system due to LLM unavailability",
        }

        # Extract text for analysis
        all_text = ""
        if "clinical_info" in extracted_entities:
            if "chief_complaint" in extracted_entities["clinical_info"]:
                all_text += extracted_entities["clinical_info"]["chief_complaint"] + " "
            if "clinical_history" in extracted_entities["clinical_info"]:
                all_text += (
                    extracted_entities["clinical_info"]["clinical_history"] + " "
                )
            if "diagnoses" in extracted_entities["clinical_info"]:
                if isinstance(extracted_entities["clinical_info"]["diagnoses"], list):
                    all_text += (
                        " ".join(extracted_entities["clinical_info"]["diagnoses"]) + " "
                    )

        all_text = all_text.lower()

        # Check for specialty indicators
        specialties = []

        # Cardiology
        if any(
            keyword in all_text
            for keyword in [
                "heart",
                "cardiac",
                "chest pain",
                "murmur",
                "arrhythmia",
                "tachycardia",
                "bradycardia",
            ]
        ):
            specialties.append(
                {
                    "specialty": "Cardiology",
                    "importance": (
                        "primary"
                        if "heart failure" in all_text or "cardiac arrest" in all_text
                        else "secondary"
                    ),
                    "reasoning": "Cardiac symptoms or history mentioned",
                }
            )
            result["potential_conditions"].append("Cardiac condition")

        # Pulmonology
        if any(
            keyword in all_text
            for keyword in [
                "respiratory",
                "breathing",
                "lung",
                "asthma",
                "pneumonia",
                "bronchiolitis",
                "cough",
            ]
        ):
            specialties.append(
                {
                    "specialty": "Pulmonology",
                    "importance": (
                        "primary"
                        if "respiratory distress" in all_text
                        or "breathing difficulty" in all_text
                        else "secondary"
                    ),
                    "reasoning": "Respiratory symptoms or history mentioned",
                }
            )
            result["potential_conditions"].append("Respiratory condition")

        # Neurology
        if any(
            keyword in all_text
            for keyword in [
                "neurological",
                "seizure",
                "stroke",
                "brain",
                "headache",
                "altered mental status",
            ]
        ):
            specialties.append(
                {
                    "specialty": "Neurology",
                    "importance": (
                        "primary"
                        if "seizure" in all_text or "stroke" in all_text
                        else "secondary"
                    ),
                    "reasoning": "Neurological symptoms or history mentioned",
                }
            )
            result["potential_conditions"].append("Neurological condition")

        # Infectious Disease
        if any(
            keyword in all_text
            for keyword in ["infection", "fever", "sepsis", "meningitis"]
        ):
            specialties.append(
                {
                    "specialty": "Infectious Disease",
                    "importance": (
                        "primary"
                        if "sepsis" in all_text or "meningitis" in all_text
                        else "secondary"
                    ),
                    "reasoning": "Infectious symptoms or history mentioned",
                }
            )
            result["potential_conditions"].append("Infectious condition")

        # Set the required specialties
        result["required_specialties"] = specialties

        # Determine care level
        if (
            "care_needs" in extracted_entities
            and "suggested_care_level" in extracted_entities["care_needs"]
        ):
            result["recommended_care_level"] = extracted_entities["care_needs"][
                "suggested_care_level"
            ]
        elif "vital_signs" in extracted_entities:
            vitals = extracted_entities["vital_signs"]
            # Check for critical vitals
            if any(
                [
                    "hr" in vitals
                    and isinstance(vitals["hr"], (int, float))
                    and (vitals["hr"] > 180 or vitals["hr"] < 60),
                    "rr" in vitals
                    and isinstance(vitals["rr"], (int, float))
                    and (vitals["rr"] > 40 or vitals["rr"] < 10),
                    "o2" in vitals
                    and isinstance(vitals["o2"], str)
                    and vitals["o2"].rstrip("%").isdigit()
                    and int(vitals["o2"].rstrip("%")) < 90,
                ]
            ):
                result["recommended_care_level"] = "ICU"
                result["care_level_reasoning"] = "Critical vital signs detected"

        # Check NICU criteria
        if (
            "demographics" in extracted_entities
            and "age" in extracted_entities["demographics"]
        ):
            if extracted_entities["demographics"]["age"] < 1:
                result["recommended_care_level"] = "NICU"
                result["care_level_reasoning"] = "Patient is an infant under 1 year"

        # Generate basic clinical summary
        summary_parts = []
        if "demographics" in extracted_entities:
            demo = extracted_entities["demographics"]
            age_str = f"{demo.get('age', '?')} year-old" if "age" in demo else ""
            gender_str = demo.get("gender", "")
            if age_str or gender_str:
                summary_parts.append(f"{age_str} {gender_str}".strip())

        if (
            "clinical_info" in extracted_entities
            and "chief_complaint" in extracted_entities["clinical_info"]
        ):
            summary_parts.append(
                f"presenting with {extracted_entities['clinical_info']['chief_complaint']}"
            )

        if specialties:
            specialty_str = ", ".join([s["specialty"] for s in specialties[:2]])
            summary_parts.append(f"requiring {specialty_str}")

        summary_parts.append(f"at {result['recommended_care_level']} level of care")

        result["clinical_summary"] = " ".join(summary_parts)

        return result
