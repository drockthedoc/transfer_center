"""
Extractors for the exclusion criteria parser.

This module contains functions for extracting specific information from text,
such as departments, conditions, age restrictions, and weight restrictions.
"""

import re
import subprocess
from typing import Any, Dict, List, Optional

from src.utils.exclusion.constants import CONDITION_KEYWORDS, DEPARTMENT_MAPPING


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF file using PyPDF2.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Extracted text as a string
    """
    try:
        # Use pdftotext command-line utility (more reliable than PyPDF2 for complex docs)
        cmd = ["pdftotext", "-layout", pdf_path, "-"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        text = result.stdout

        # Clean up the text
        text = re.sub(r"\s+", " ", text)  # Replace multiple spaces with a single space
        text = text.replace("\f", "\n\n")  # Form feeds to paragraph breaks

        return text
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print(f"Error extracting text from PDF: {e}")
        # Fall back to PyPDF2 if pdftotext is not available
        try:
            import PyPDF2

            with open(pdf_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n\n"
                return text
        except Exception as e2:
            print(f"PyPDF2 fallback also failed: {e2}")
            return ""


def identify_department(text: str) -> str:
    """
    Identify the department or specialty associated with a section of text.
    Returns the most likely department name.

    Args:
        text: Text to analyze

    Returns:
        Department name as string
    """
    text = text.lower()

    # Count matches for each department
    matches = {}
    for dept, keywords in DEPARTMENT_MAPPING.items():
        count = sum(1 for keyword in keywords if keyword in text)
        if count > 0:
            matches[dept] = count

    # Return the department with the most matches, or "general" if none found
    if matches:
        return max(matches.items(), key=lambda x: x[1])[0]
    return "general"


def identify_conditions(text: str) -> List[str]:
    """
    Identify medical conditions mentioned in the text.

    Args:
        text: Text to analyze

    Returns:
        List of condition categories
    """
    text = text.lower()

    conditions = []
    for condition, keywords in CONDITION_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            conditions.append(condition)

    return conditions


def extract_age_restriction(text: str) -> Dict[str, Any]:
    """
    Extract age restrictions from text.
    Returns a dictionary with keys 'minimum' and/or 'maximum'.

    Args:
        text: Text to analyze

    Returns:
        Dictionary with age restrictions
    """
    text = text.lower()
    result = {}

    # Look for minimum age restrictions
    min_patterns = [
        r"(?:patient|child(?:ren)?|age)(?:\s+must\s+be|\s+is|\s+are)?\s+(?:>|≥|≧|>=|greater\s+than|at\s+least|older\s+than|minimum)\s*(\d+\.?\d*)\s*(?:years?|yrs?|yo|y\.?o\.?|months?|weeks?|days?)?",
        r"(?:minimum|min)(?:\s+age)?\s+(?:of|is|=)?\s*(\d+\.?\d*)\s*(?:years?|yrs?|yo|y\.?o\.?|months?|weeks?|days?)?",
        r"(?:patients?|children)\s+(?:aged|aging)?\s+(\d+\.?\d*)\s*(?:\+|or\s+older|and\s+older|and\s+above|and\s+up)",
        r"(\d+\.?\d*)\s*(?:years?|yrs?|yo|y\.?o\.?|months?|weeks?|days?)?\s+(?:or|and)\s+older",
    ]

    for pattern in min_patterns:
        matches = re.findall(pattern, text)
        if matches:
            try:
                result["minimum"] = float(matches[0])
                break
            except (ValueError, IndexError):
                continue

    # Look for maximum age restrictions
    max_patterns = [
        r"(?:patient|child(?:ren)?|age)(?:\s+must\s+be|\s+is|\s+are)?\s+(?:<|≤|≦|<=|less\s+than|younger\s+than|maximum)\s*(\d+\.?\d*)\s*(?:years?|yrs?|yo|y\.?o\.?|months?|weeks?|days?)?",
        r"(?:maximum|max)(?:\s+age)?\s+(?:of|is|=)?\s*(\d+\.?\d*)\s*(?:years?|yrs?|yo|y\.?o\.?|months?|weeks?|days?)?",
        r"(?:up\s+to|under)\s+(?:age\s+)?(\d+\.?\d*)\s*(?:years?|yrs?|yo|y\.?o\.?|months?|weeks?|days?)?",
        r"(\d+\.?\d*)\s*(?:years?|yrs?|yo|y\.?o\.?|months?|weeks?|days?)?\s+(?:or|and)\s+younger",
    ]

    for pattern in max_patterns:
        matches = re.findall(pattern, text)
        if matches:
            try:
                result["maximum"] = float(matches[0])
                break
            except (ValueError, IndexError):
                continue

    return result


def extract_weight_restriction(text: str) -> Dict[str, Any]:
    """
    Extract weight restrictions from text.
    Returns a dictionary with keys 'minimum' and/or 'maximum'.

    Args:
        text: Text to analyze

    Returns:
        Dictionary with weight restrictions
    """
    text = text.lower()
    result = {}

    # Look for minimum weight restrictions
    min_patterns = [
        r"(?:patient|child(?:ren)?|weight)(?:\s+must\s+be|\s+is|\s+are)?\s+(?:>|≥|≧|>=|greater\s+than|at\s+least|heavier\s+than|minimum)\s*(\d+\.?\d*)\s*(?:kg|kilograms?|pounds?|lbs?)?",
        r"(?:minimum|min)(?:\s+weight)?\s+(?:of|is|=)?\s*(\d+\.?\d*)\s*(?:kg|kilograms?|pounds?|lbs?)?",
        r"(?:patients?|children)\s+weighing\s+(\d+\.?\d*)\s*(?:kg|kilograms?|pounds?|lbs?)?\s+(?:\+|or\s+more|and\s+more|and\s+above)",
    ]

    for pattern in min_patterns:
        matches = re.findall(pattern, text)
        if matches:
            try:
                weight = float(matches[0])
                # Convert to kg if in pounds (assuming pound if > 50)
                if "lb" in text or "pound" in text or weight > 50:
                    weight = weight / 2.2046
                result["minimum"] = round(weight, 1)
                break
            except (ValueError, IndexError):
                continue

    # Look for maximum weight restrictions
    max_patterns = [
        r"(?:patient|child(?:ren)?|weight)(?:\s+must\s+be|\s+is|\s+are)?\s+(?:<|≤|≦|<=|less\s+than|lighter\s+than|maximum)\s*(\d+\.?\d*)\s*(?:kg|kilograms?|pounds?|lbs?)?",
        r"(?:maximum|max)(?:\s+weight)?\s+(?:of|is|=)?\s*(\d+\.?\d*)\s*(?:kg|kilograms?|pounds?|lbs?)?",
        r"(?:up\s+to|under)\s+(?:weight\s+)?(\d+\.?\d*)\s*(?:kg|kilograms?|pounds?|lbs?)?",
    ]

    for pattern in max_patterns:
        matches = re.findall(pattern, text)
        if matches:
            try:
                weight = float(matches[0])
                # Convert to kg if in pounds (assuming pound if > 50)
                if "lb" in text or "pound" in text or weight > 50:
                    weight = weight / 2.2046
                result["maximum"] = round(weight, 1)
                break
            except (ValueError, IndexError):
                continue

    return result
