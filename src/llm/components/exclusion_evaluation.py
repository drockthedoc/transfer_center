"""
Exclusion evaluation component for LLM integration.

This module handles the evaluation of exclusion criteria based on extracted clinical entities.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ExclusionEvaluator:
    """Handles evaluation of exclusion criteria based on extracted clinical entities."""

    def __init__(self, client, model: str):
        """
        Initialize the exclusion evaluator.

        Args:
            client: OpenAI client instance
            model: Name of the model to use
        """
        self.client = client
        self.model = model

    def evaluate_exclusions(
        self, extracted_entities: Dict[str, Any], exclusion_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate exclusion criteria based on extracted clinical entities.

        Args:
            extracted_entities: Dictionary of extracted clinical entities
            exclusion_criteria: Dictionary of exclusion criteria by campus

        Returns:
            Dictionary with exclusion criteria evaluation
        """
        logger.info("Running exclusion criteria evaluation...")

        # Construct the prompt for exclusion evaluation
        prompt = self._build_evaluation_prompt(extracted_entities, exclusion_criteria)

        try:
            # Call the LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a hospital transfer coordinator.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Slight variation allowed
                max_tokens=2000,
            )

            # Extract JSON response
            content = response.choices[0].message.content
            logger.debug(f"Exclusion evaluation raw response: {content}")

            # Parse JSON from response
            try:
                # Find JSON content between triple backticks
                if "```json" in content and "```" in content.split("```json", 1)[1]:
                    json_content = content.split("```json", 1)[1].split("```", 1)[0]
                    evaluation = json.loads(json_content)
                elif "```" in content and "```" in content.split("```", 1)[1]:
                    json_content = content.split("```", 1)[1].split("```", 1)[0]
                    evaluation = json.loads(json_content)
                else:
                    # Try direct JSON parsing
                    evaluation = json.loads(content)

                logger.info("Exclusion evaluation successful")
                return evaluation
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON from LLM response: {e}")
                # Fallback to simple evaluation
                return self._fallback_evaluation(extracted_entities, exclusion_criteria)

        except Exception as e:
            logger.error(f"Error during exclusion evaluation: {e}")
            return self._fallback_evaluation(extracted_entities, exclusion_criteria)

    def _build_evaluation_prompt(
        self, extracted_entities: Dict[str, Any], exclusion_criteria: Dict[str, Any]
    ) -> str:
        """
        Build the prompt for exclusion evaluation.

        Args:
            extracted_entities: Dictionary of extracted clinical entities
            exclusion_criteria: Dictionary of exclusion criteria by campus

        Returns:
            Formatted prompt string
        """
        # Format the extracted entities as a clean string
        entities_str = json.dumps(extracted_entities, indent=2)

        # Create a simplified version of exclusion criteria
        simplified_exclusions = {}
        for campus_id, campus_data in exclusion_criteria.get("campuses", {}).items():
            simplified_exclusions[campus_id] = {
                "general_exclusions": campus_data.get("general_exclusions", []),
                "departments": {},
            }

            for dept_id, dept_data in campus_data.get("departments", {}).items():
                simplified_exclusions[campus_id]["departments"][dept_id] = {
                    "name": dept_data.get("name", dept_id),
                    "exclusions": dept_data.get("exclusions", []),
                    "age_restrictions": dept_data.get("age_restrictions", {}),
                    "weight_restrictions": dept_data.get("weight_restrictions", {}),
                }

        # Format the exclusion criteria as a clean string, limiting length
        exclusions_str = json.dumps(simplified_exclusions, indent=2)

        return f"""
Evaluate if the patient meets any exclusion criteria for hospital campuses.

PATIENT INFORMATION:
{entities_str}

EXCLUSION CRITERIA BY CAMPUS:
{exclusions_str}

Check if the patient's condition matches any exclusion criteria for each campus.
Consider age restrictions, weight restrictions, and specific medical conditions.

Provide the following in JSON format:
1. For each campus, list any matched exclusion criteria
2. Evidence from the patient information that supports each match
3. Overall assessment if the patient should be excluded from each campus

JSON Output:
```json
{{
  "campus_exclusions": {{
    "campus_id": {{
      "is_excluded": true/false,
      "exclusion_matches": [
        {{
          "exclusion": "Text of the matched exclusion",
          "department": "Department name",
          "evidence": "Patient information that matches this exclusion",
          "confidence": 0-100
        }}
      ],
      "overall_reasoning": "Brief explanation of exclusion decision"
    }}
  }},
  "recommended_campus": "ID of recommended campus based on fewest exclusions",
  "recommendation_reasoning": "Explanation for campus recommendation"
}}
```

Respond only with the JSON output.
"""

    def _fallback_evaluation(
        self, extracted_entities: Dict[str, Any], exclusion_criteria: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fallback evaluation method using rule-based approach.

        Args:
            extracted_entities: Dictionary of extracted clinical entities
            exclusion_criteria: Dictionary of exclusion criteria by campus

        Returns:
            Dictionary with exclusion criteria evaluation
        """
        # Initialize result
        result = {
            "campus_exclusions": {},
            "recommended_campus": None,
            "recommendation_reasoning": "Based on rule-based evaluation due to LLM unavailability",
        }

        # Extract patient information for matching
        patient_age = None
        if (
            "demographics" in extracted_entities
            and "age" in extracted_entities["demographics"]
        ):
            patient_age = extracted_entities["demographics"]["age"]

        patient_weight = None
        if (
            "demographics" in extracted_entities
            and "weight" in extracted_entities["demographics"]
        ):
            patient_weight = extracted_entities["demographics"]["weight"]

        # Create a single text string for simple text matching
        patient_text = ""

        if "clinical_info" in extracted_entities:
            if "chief_complaint" in extracted_entities["clinical_info"]:
                patient_text += (
                    extracted_entities["clinical_info"]["chief_complaint"] + " "
                )
            if "clinical_history" in extracted_entities["clinical_info"]:
                patient_text += (
                    extracted_entities["clinical_info"]["clinical_history"] + " "
                )
            if "diagnoses" in extracted_entities["clinical_info"]:
                if isinstance(extracted_entities["clinical_info"]["diagnoses"], list):
                    patient_text += (
                        " ".join(extracted_entities["clinical_info"]["diagnoses"]) + " "
                    )

        patient_text = patient_text.lower()

        # Evaluate each campus
        campus_matches = {}

        for campus_id, campus_data in exclusion_criteria.get("campuses", {}).items():
            matches = []

            # Check general exclusions
            for exclusion in campus_data.get("general_exclusions", []):
                exclusion_lower = exclusion.lower()
                # Simple text matching
                if any(keyword in patient_text for keyword in exclusion_lower.split()):
                    matches.append(
                        {
                            "exclusion": exclusion,
                            "department": "General",
                            "evidence": "Text match in patient information",
                            "confidence": 70,
                        }
                    )

            # Check department-specific exclusions
            for dept_id, dept_data in campus_data.get("departments", {}).items():
                # Check age restrictions
                age_restrictions = dept_data.get("age_restrictions", {})
                if patient_age is not None and age_restrictions:
                    if (
                        "minimum" in age_restrictions
                        and patient_age < age_restrictions["minimum"]
                    ):
                        matches.append(
                            {
                                "exclusion": f"Age restriction: minimum {age_restrictions['minimum']} years",
                                "department": dept_data.get("name", dept_id),
                                "evidence": f"Patient age ({patient_age}) below minimum",
                                "confidence": 95,
                            }
                        )
                    if (
                        "maximum" in age_restrictions
                        and patient_age > age_restrictions["maximum"]
                    ):
                        matches.append(
                            {
                                "exclusion": f"Age restriction: maximum {age_restrictions['maximum']} years",
                                "department": dept_data.get("name", dept_id),
                                "evidence": f"Patient age ({patient_age}) above maximum",
                                "confidence": 95,
                            }
                        )

                # Check weight restrictions
                weight_restrictions = dept_data.get("weight_restrictions", {})
                if patient_weight is not None and weight_restrictions:
                    if (
                        "minimum" in weight_restrictions
                        and patient_weight < weight_restrictions["minimum"]
                    ):
                        matches.append(
                            {
                                "exclusion": f"Weight restriction: minimum {weight_restrictions['minimum']} kg",
                                "department": dept_data.get("name", dept_id),
                                "evidence": f"Patient weight ({patient_weight}) below minimum",
                                "confidence": 95,
                            }
                        )
                    if (
                        "maximum" in weight_restrictions
                        and patient_weight > weight_restrictions["maximum"]
                    ):
                        matches.append(
                            {
                                "exclusion": f"Weight restriction: maximum {weight_restrictions['maximum']} kg",
                                "department": dept_data.get("name", dept_id),
                                "evidence": f"Patient weight ({patient_weight}) above maximum",
                                "confidence": 95,
                            }
                        )

                # Check specific exclusions
                for exclusion in dept_data.get("exclusions", []):
                    exclusion_lower = exclusion.lower()
                    # Simple text matching
                    if any(
                        keyword in patient_text for keyword in exclusion_lower.split()
                    ):
                        matches.append(
                            {
                                "exclusion": exclusion,
                                "department": dept_data.get("name", dept_id),
                                "evidence": "Text match in patient information",
                                "confidence": 70,
                            }
                        )

            # Determine if campus is excluded
            is_excluded = len(matches) > 0

            # Add to result
            result["campus_exclusions"][campus_id] = {
                "is_excluded": is_excluded,
                "exclusion_matches": matches,
                "overall_reasoning": f"{'Excluded' if is_excluded else 'Not excluded'} based on rule-based matching",
            }

            # Track match count for recommendation
            campus_matches[campus_id] = len(matches)

        # Determine recommended campus (one with fewest exclusions)
        if campus_matches:
            min_exclusions = min(campus_matches.values())
            eligible_campuses = [
                campus_id
                for campus_id, count in campus_matches.items()
                if count == min_exclusions
            ]

            if eligible_campuses:
                result["recommended_campus"] = eligible_campuses[0]
                if min_exclusions == 0:
                    result["recommendation_reasoning"] = (
                        f"Campus {eligible_campuses[0]} has no exclusion matches"
                    )
                else:
                    result["recommendation_reasoning"] = (
                        f"Campus {eligible_campuses[0]} has fewest exclusion matches ({min_exclusions})"
                    )

        return result
