"""
Entity extraction component for LLM integration.

This module handles the extraction of clinical entities from patient text.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from src.llm.utils import robust_json_parser
from src.llm.llm_logging import get_llm_logger

logger = logging.getLogger(__name__)
llm_logger = get_llm_logger()


class EntityExtractor:
    """Handles extraction of clinical entities from text using LLM."""

    def __init__(self, client, model: str):
        """
        Initialize the entity extractor.

        Args:
            client: OpenAI client instance
            model: Name of the model to use
        """
        self.client = client
        self.model = model

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract clinical entities from patient text.

        Args:
            text: Clinical text to process

        Returns:
            Dictionary of extracted entities
        """
        logger.info("Running entity extraction...")

        # Construct the prompt for entity extraction
        prompt = self._build_extraction_prompt(text)
        
        # Prepare messages for the LLM
        messages = [
            {
                "role": "system",
                "content": "You are a clinical data extraction assistant.",
            },
            {"role": "user", "content": prompt},
        ]
        
        # Log the prompt being sent to the LLM
        interaction_id = llm_logger.log_prompt(
            component="EntityExtractor",
            method="extract_entities",
            prompt=prompt,
            model=self.model,
            messages=messages,
            metadata={"text_length": len(text), "text_sample": text[:100]}
        )

        try:
            # Call the LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,  # Use deterministic output for extractions
                max_tokens=2000,
            )

            # Extract JSON response
            content = response.choices[0].message.content
            logger.debug(f"Entity extraction raw response: {content}")

            # Parse JSON from response using the robust parser
            entities = robust_json_parser(content)
            
            if entities:
                logger.info("Entity extraction successful using robust parser")
                # Log the successful response
                llm_logger.log_response(
                    interaction_id=interaction_id,
                    output_data=entities,
                    success=True,
                    metadata={"parser": "robust_json_parser"}
                )
                return entities
            else:
                logger.warning(
                    "Robust JSON parsing failed, falling back to rule-based extraction"
                )
                # Log the failed parsing
                llm_logger.log_response(
                    interaction_id=interaction_id,
                    output_data=content,
                    success=False,
                    error="JSON parsing failed",
                    metadata={"fallback": "rule-based"}
                )
                # Fallback to simple extraction
                return self._fallback_extraction(text)

        except Exception as e:
            logger.error(f"Error during entity extraction: {e}")
            # Log the error
            llm_logger.log_response(
                interaction_id=interaction_id,
                output_data=None,
                success=False,
                error=str(e),
                metadata={"fallback": "rule-based", "exception": type(e).__name__}
            )
            return self._fallback_extraction(text)

    def _build_extraction_prompt(self, text: str) -> str:
        """
        Build the prompt for entity extraction.

        Args:
            text: Clinical text to process

        Returns:
            Formatted prompt string
        """
        return f"""
Extract the following information from the clinical text in JSON format:

1. Demographics:
   - age: Age of the patient (numeric value only)
   - gender: Gender of the patient ("male", "female", or "unknown")
   - weight: Weight in kg if available (numeric value only)

2. Vital Signs:
   - hr: Heart rate (numeric value only)
   - rr: Respiratory rate (numeric value only)
   - bp: Blood pressure as "systolic/diastolic"
   - temp: Temperature in Celsius (numeric value only)
   - o2: Oxygen saturation with percentage sign (e.g., "95%")

3. Clinical Information:
   - chief_complaint: Main presenting complaint (one sentence)
   - clinical_history: Brief summary of clinical history (2-3 sentences)
   - diagnoses: List of diagnoses mentioned
   - medications: List of medications mentioned
   - allergies: List of allergies mentioned
   - procedures: List of procedures mentioned or performed

4. Care Needs:
   - suggested_care_level: Suggested level of care ("General", "ICU", "PICU", or "NICU")
   - requires_ventilator: Boolean indicating if ventilator support is mentioned
   - requires_isolation: Boolean indicating if isolation is mentioned
   - requires_telemetry: Boolean indicating if cardiac monitoring is mentioned
   - requires_specialty_care: List of specialties mentioned (e.g., "Cardiology", "Neurology")

Please format your response as a JSON object. Only include fields where information is explicitly provided in the text.

Clinical Text:
{text}

JSON Output:
```json
"""

    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """
        Fallback extraction method using simple pattern matching.

        Args:
            text: Clinical text to process

        Returns:
            Dictionary of extracted entities
        """
        import re

        result = {
            "demographics": {},
            "vital_signs": {},
            "clinical_info": {},
            "care_needs": {},
        }

        # Extract age
        age_match = re.search(
            r"(\d+)(?:\s*-|\s+)(?:year|yr|y)[s\s]*(?:old)?", text, re.IGNORECASE
        )
        if age_match:
            result["demographics"]["age"] = int(age_match.group(1))

        # Extract gender
        if re.search(r"\b(?:male|boy|man)\b", text, re.IGNORECASE):
            result["demographics"]["gender"] = "male"
        elif re.search(r"\b(?:female|girl|woman)\b", text, re.IGNORECASE):
            result["demographics"]["gender"] = "female"

        # Extract vital signs
        hr_match = re.search(r"(?:HR|heart rate|pulse)[:\s]+(\d+)", text, re.IGNORECASE)
        if hr_match:
            result["vital_signs"]["hr"] = int(hr_match.group(1))

        rr_match = re.search(
            r"(?:RR|resp(?:iratory)? rate)[:\s]+(\d+)", text, re.IGNORECASE
        )
        if rr_match:
            result["vital_signs"]["rr"] = int(rr_match.group(1))

        bp_match = re.search(
            r"(?:BP|blood pressure)[:\s]+(\d+)[/\\](\d+)", text, re.IGNORECASE
        )
        if bp_match:
            result["vital_signs"]["bp"] = f"{bp_match.group(1)}/{bp_match.group(2)}"

        temp_match = re.search(
            r"(?:temp|temperature)[:\s]+(\d+\.?\d*)", text, re.IGNORECASE
        )
        if temp_match:
            result["vital_signs"]["temp"] = float(temp_match.group(1))

        o2_match = re.search(
            r"(?:O2|oxygen|sat|saturation)[:\s]+(\d+)(?:\s*%)?", text, re.IGNORECASE
        )
        if o2_match:
            result["vital_signs"]["o2"] = f"{o2_match.group(1)}%"

        # Extract clinical info - first sentence as chief complaint
        sentences = text.split(".")
        if sentences:
            result["clinical_info"]["chief_complaint"] = sentences[0].strip()

        # Extract suggested care level
        if re.search(r"\b(?:NICU|neonatal|infant|newborn)\b", text, re.IGNORECASE):
            result["care_needs"]["suggested_care_level"] = "NICU"
        elif re.search(r"\b(?:PICU|pediatric intensive)\b", text, re.IGNORECASE):
            result["care_needs"]["suggested_care_level"] = "PICU"
        elif re.search(
            r"\b(?:ICU|intensive care|critical care)\b", text, re.IGNORECASE
        ):
            result["care_needs"]["suggested_care_level"] = "ICU"
        else:
            result["care_needs"]["suggested_care_level"] = "General"

        return result
