"""
JSON extraction utilities for processing LLM outputs in the Transfer Center application.

This module provides utility functions for extracting JSON data from various formats,
including triple-quoted markdown code blocks often returned by LLMs.
"""

import re
import json
import logging
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

def extract_json_from_markdown(text: Union[str, Dict, Any]) -> Union[Dict, Any]:
    """Extract JSON from markdown code blocks or raw text.
    
    This function handles various formats of JSON data that might be returned by LLMs:
    1. JSON data already in dictionary format
    2. JSON data inside markdown code blocks (```json ... ```)
    3. Raw JSON strings
    
    Args:
        text: Text or object that might contain JSON data
        
    Returns:
        Extracted JSON as a dictionary if successful, or the original text if extraction fails
    """
    # If it's already a dictionary, return it
    if isinstance(text, dict):
        return text
        
    # If it's not a string, we can't extract JSON
    if not isinstance(text, str):
        return text
        
    # Look for JSON in markdown code blocks (triple backticks)
    # This pattern looks for ```json followed by content and ending with ```
    json_pattern = r'```(?:json)?\s*\n([\s\S]*?)\n\s*```'
    match = re.search(json_pattern, text)
    
    if match:
        try:
            # Try to parse the content inside the code block
            json_content = match.group(1).strip()
            logger.debug(f"Extracted JSON from markdown code block: {json_content[:100]}...")
            return json.loads(json_content)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from markdown code block: {e}")
            # Fall through to try parsing the whole text
    
    # If no code block is found or parsing failed, try to parse the whole text as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse text as JSON: {e}")
        return text  # Return the original text if all parsing attempts fail
