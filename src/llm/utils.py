"""
Utility functions for LLM-related operations.

This module provides helper functions used across the LLM components, including
robust JSON parsing and error handling.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def robust_json_parser(text: str) -> Dict[str, Any]:
    """
    Robustly extract and parse JSON from LLM response text.

    This function attempts multiple strategies to parse JSON:
    1. Parse the entire text as JSON
    2. Extract JSON between code blocks (```json ... ```)
    3. Extract JSON between regular code blocks (``` ... ```)
    4. Find any JSON-like structure in the text using regex
    5. Attempt to fix common JSON formatting issues and retry parsing
    6. Handle truncated JSON by attempting to complete missing brackets
    7. Handle repetitive content by finding the first complete JSON structure

    Args:
        text: Text containing JSON to parse

    Returns:
        Parsed JSON dictionary or empty dict if parsing fails
    """
    if not text or not isinstance(text, str):
        logger.error("Invalid input for JSON parsing")
        return {}

    logger.debug(f"Attempting to parse JSON from text: {text[:100]}...")

    # Strategy 1: Try parsing the entire text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.debug("Failed to parse entire text as JSON, trying alternative methods")

    # Strategy 2: Handle repeated JSON blocks (common in LLM outputs)
    # Look for first complete JSON object within code blocks
    json_block_patterns = [
        # Pattern for ```json ... ``` blocks
        r"```json\s*([\s\S]*?)\s*```",
        # Pattern for ``` ... ``` blocks
        r"```\s*([\s\S]*?)\s*```",
    ]

    for pattern in json_block_patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Try each match separately
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    # Try to fix this particular match
                    try:
                        # Fix common JSON issues
                        fixed_match = re.sub(r",\s*}", "}", match)
                        fixed_match = re.sub(r",\s*]", "]", fixed_match)
                        return json.loads(fixed_match)
                    except json.JSONDecodeError:
                        continue

    # Strategy 3: Find any complete JSON-like structure in the text
    json_pattern = r"\{[\s\S]*?\}"
    matches = re.findall(json_pattern, text)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    # Strategy 4: Handle truncated JSON (common with token limits)
    # Try to balance brackets and complete the JSON
    try:
        # Extract potential JSON structure
        json_start = text.find("{")
        if json_start >= 0:
            text_subset = text[json_start:]

            # Count opening and closing braces
            open_braces = text_subset.count("{")
            close_braces = text_subset.count("}")

            # If unbalanced, add missing closing braces
            if open_braces > close_braces:
                text_subset += "}" * (open_braces - close_braces)

            # Remove trailing commas before closing brackets
            fixed_text = re.sub(r",\s*}", "}", text_subset)
            fixed_text = re.sub(r",\s*]", "]", fixed_text)

            # Try parsing the completed JSON
            try:
                return json.loads(fixed_text)
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.debug(f"Error during bracket balancing: {e}")

    # Strategy 5: Try more aggressive fixes for common issues
    try:
        # Start with the most likely JSON part (from the first '{' to the end)
        potential_json = text[text.find("{") :]

        # Fix unquoted keys (words followed by colon)
        fixed_text = re.sub(r"([{,]\s*)(\w+)(\s*:)", r'\1"\2"\3', potential_json)

        # Fix trailing commas
        fixed_text = re.sub(r",\s*}", "}", fixed_text)
        fixed_text = re.sub(r",\s*]", "]", fixed_text)

        # Balance brackets if needed
        open_braces = fixed_text.count("{")
        close_braces = fixed_text.count("}")
        if open_braces > close_braces:
            fixed_text += "}" * (open_braces - close_braces)

        # Try parsing again
        try:
            return json.loads(fixed_text)
        except json.JSONDecodeError:
            pass
    except Exception as e:
        logger.debug(f"Error during aggressive JSON fixing: {e}")

    # If all strategies fail
    logger.error("All JSON parsing attempts failed")
    return {}


def extract_fields_safely(
    data: Dict[str, Any], field_path: str, default: Any = None
) -> Any:
    """
    Safely extract nested fields from a dictionary without raising KeyError.

    Args:
        data: Dictionary to extract from
        field_path: Path to field using dot notation (e.g., "patient.vitals.hr")
        default: Default value to return if field not found

    Returns:
        Field value or default if not found
    """
    if not data:
        return default

    parts = field_path.split(".")
    current = data

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default

    return current
