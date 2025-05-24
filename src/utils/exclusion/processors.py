"""
Processors for the exclusion criteria parser.

This module contains functions for processing different sections and document types
for exclusion criteria parsing.
"""

import re
from typing import Any, Dict, List

from src.utils.exclusion.extractors import (
    extract_age_restriction,
    extract_weight_restriction,
    identify_conditions,
    identify_department,
)


def parse_austin_exclusions(text: str) -> Dict[str, Any]:
    """
    Parse the Austin campus exclusion criteria PDF.

    Args:
        text: Text content of the PDF

    Returns:
        Dictionary of structured exclusion data
    """
    # Initialize result structure
    result = {
        "campus": "austin",
        "departments": {},
        "general_exclusions": [],
    }

    # Split into sections - Austin format typically has sections for different units
    sections = re.split(r"\n\s*\n+", text)

    current_dept = "general"
    for section in sections:
        # Skip very short sections (likely headers or page numbers)
        if len(section.strip()) < 50:
            continue

        # Check if this is a department/unit header
        first_line = section.strip().split("\n")[0].strip()
        if first_line.isupper() and len(first_line) < 100:
            # Looks like a header, identify department
            dept = identify_department(first_line)
            current_dept = dept

            # Initialize department if not exists
            if current_dept not in result["departments"]:
                result["departments"][current_dept] = {
                    "name": current_dept,
                    "exclusions": [],
                    "conditions": [],
                    "age_restrictions": {},
                    "weight_restrictions": {},
                }

            # Skip processing the header as content
            section = "\n".join(section.strip().split("\n")[1:])

        # Extract bullet points or numbered items as exclusions
        bullet_pattern = r"(?:^|\n)(?:\s*[-•*]\s*|\s*\d+\.\s*)(.+?)(?=(?:\n\s*[-•*]|\n\s*\d+\.|\n\s*\n|$))"
        exclusions = re.findall(bullet_pattern, section, re.DOTALL)

        # If no bullet points found, try paragraph breaks
        if not exclusions:
            exclusions = [p.strip() for p in section.split("\n") if p.strip()]

        # Process each exclusion
        for item in exclusions:
            # Clean up the item
            item = item.strip()
            if not item:
                continue

            # Skip section headers that got captured
            if item.isupper() and len(item) < 100:
                continue

            # Add to appropriate list
            if current_dept == "general":
                result["general_exclusions"].append(item)
            else:
                result["departments"][current_dept]["exclusions"].append(item)

                # Extract additional metadata
                conditions = identify_conditions(item)
                if conditions:
                    result["departments"][current_dept]["conditions"].extend(conditions)

                age_restrictions = extract_age_restriction(item)
                if age_restrictions:
                    result["departments"][current_dept]["age_restrictions"].update(
                        age_restrictions
                    )

                weight_restrictions = extract_weight_restriction(item)
                if weight_restrictions:
                    result["departments"][current_dept]["weight_restrictions"].update(
                        weight_restrictions
                    )

    # Remove duplicates from conditions
    for dept in result["departments"].values():
        dept["conditions"] = list(set(dept["conditions"]))

    return result


def parse_community_exclusions(text: str) -> Dict[str, Any]:
    """
    Parse the Community campus exclusion criteria PDF.
    Handles the complex table structure with columns for different types of exclusions.

    Args:
        text: Text content of the PDF

    Returns:
        Dictionary of structured exclusion data
    """
    # Initialize result structure
    result = {
        "campus": "community",
        "departments": {},
        "general_exclusions": [],
    }

    # Community PDFs often have a table-like structure
    # Split into sections by page breaks or large whitespace
    sections = re.split(r"\f|\n\s*\n\s*\n+", text)

    for section in sections:
        # Skip very short sections
        if len(section.strip()) < 50:
            continue

        # Process each section
        process_community_table_section(section, result)

    # Process special sections that might not fit the table structure
    process_special_sections(text, result)

    # Remove duplicates from conditions
    for dept in result["departments"].values():
        dept["conditions"] = list(set(dept["conditions"]))

    return result


def process_community_table_section(section: str, result: Dict[str, Any]) -> None:
    """
    Process a section of the Community campus exclusion table.

    Args:
        section: Text of a section from the table
        result: Result dictionary to update
    """
    # Try to identify if this section has a department heading
    lines = section.strip().split("\n")

    # Check if first line could be a header
    current_dept = "general"
    if lines and lines[0].strip() and len(lines[0].strip()) < 100:
        dept = identify_department(lines[0])
        current_dept = dept

        # Initialize department if not exists
        if current_dept not in result["departments"]:
            result["departments"][current_dept] = {
                "name": current_dept,
                "exclusions": [],
                "conditions": [],
                "age_restrictions": {},
                "weight_restrictions": {},
            }

        # Remove the header from content to process
        section = "\n".join(lines[1:])

    # Community PDFs often have columns with different categories
    # Try to identify column-based content
    column_pattern = r"(?:^|\n)(?:\s*[-•*]\s*|\s*\d+\.\s*|\s*[A-Z]\.\s*)(.+?)(?=(?:\n\s*[-•*]|\n\s*\d+\.|\n\s*[A-Z]\.|\n\s*\n|$))"
    items = re.findall(column_pattern, section, re.DOTALL)

    # If no structured items found, just use line breaks
    if not items:
        items = [line.strip() for line in section.split("\n") if line.strip()]

    # Process each item
    for item in items:
        # Clean up the item
        item = item.strip()
        if not item:
            continue

        # Skip headers or table labels
        if item.isupper() and len(item) < 50:
            continue

        # Check if this is a new department indicator
        if ":" in item and len(item.split(":", 1)[0]) < 30:
            potential_dept = identify_department(item.split(":", 1)[0])
            if potential_dept != "general":
                current_dept = potential_dept

                # Initialize department if not exists
                if current_dept not in result["departments"]:
                    result["departments"][current_dept] = {
                        "name": current_dept,
                        "exclusions": [],
                        "conditions": [],
                        "age_restrictions": {},
                        "weight_restrictions": {},
                    }

                # Add the content after the colon as an exclusion
                content = item.split(":", 1)[1].strip()
                if content:
                    result["departments"][current_dept]["exclusions"].append(content)

                continue

        # Add to appropriate list
        if current_dept == "general":
            result["general_exclusions"].append(item)
        else:
            result["departments"][current_dept]["exclusions"].append(item)

            # Extract additional metadata
            conditions = identify_conditions(item)
            if conditions:
                result["departments"][current_dept]["conditions"].extend(conditions)

            age_restrictions = extract_age_restriction(item)
            if age_restrictions:
                result["departments"][current_dept]["age_restrictions"].update(
                    age_restrictions
                )

            weight_restrictions = extract_weight_restriction(item)
            if weight_restrictions:
                result["departments"][current_dept]["weight_restrictions"].update(
                    weight_restrictions
                )


def process_special_sections(text: str, result: Dict[str, Any]) -> None:
    """
    Process special sections in the Community PDF that might be outside the main table.

    Args:
        text: Full text of the PDF
        result: Result dictionary to update
    """
    # Look for specific sections like "Age Restrictions" or "Weight Restrictions"
    age_section_pattern = r"(?:Age\s+Restrictions?|Age\s+Criteria)(?:\s*:\s*|\s*\n\s*)(.*?)(?=\n\s*\n|\f|$)"
    age_sections = re.findall(age_section_pattern, text, re.IGNORECASE | re.DOTALL)

    for section in age_sections:
        # Extract age restrictions for each department mentioned
        dept_patterns = r"(?:^|\n)(?:\s*[-•*]\s*|\s*\d+\.\s*)?\s*([A-Za-z\s]+?)(?:\s*:\s*|\s*-\s*)(.*?)(?=\n|$)"
        dept_matches = re.findall(dept_patterns, section)

        for dept_name, criteria in dept_matches:
            dept_name = dept_name.strip().lower()
            dept = identify_department(dept_name)

            if dept != "general":
                # Initialize department if not exists
                if dept not in result["departments"]:
                    result["departments"][dept] = {
                        "name": dept,
                        "exclusions": [],
                        "conditions": [],
                        "age_restrictions": {},
                        "weight_restrictions": {},
                    }

                # Extract age restrictions
                age_restrictions = extract_age_restriction(criteria)
                if age_restrictions:
                    result["departments"][dept]["age_restrictions"].update(
                        age_restrictions
                    )

                    # Add as an exclusion too
                    age_text = f"Age restriction: "
                    if "minimum" in age_restrictions:
                        age_text += f"minimum {age_restrictions['minimum']} years"
                    if "maximum" in age_restrictions:
                        if "minimum" in age_restrictions:
                            age_text += f", "
                        age_text += f"maximum {age_restrictions['maximum']} years"

                    result["departments"][dept]["exclusions"].append(age_text)

    # Look for weight restriction sections
    weight_section_pattern = r"(?:Weight\s+Restrictions?|Weight\s+Criteria)(?:\s*:\s*|\s*\n\s*)(.*?)(?=\n\s*\n|\f|$)"
    weight_sections = re.findall(
        weight_section_pattern, text, re.IGNORECASE | re.DOTALL
    )

    for section in weight_sections:
        # Extract weight restrictions for each department mentioned
        dept_patterns = r"(?:^|\n)(?:\s*[-•*]\s*|\s*\d+\.\s*)?\s*([A-Za-z\s]+?)(?:\s*:\s*|\s*-\s*)(.*?)(?=\n|$)"
        dept_matches = re.findall(dept_patterns, section)

        for dept_name, criteria in dept_matches:
            dept_name = dept_name.strip().lower()
            dept = identify_department(dept_name)

            if dept != "general":
                # Initialize department if not exists
                if dept not in result["departments"]:
                    result["departments"][dept] = {
                        "name": dept,
                        "exclusions": [],
                        "conditions": [],
                        "age_restrictions": {},
                        "weight_restrictions": {},
                    }

                # Extract weight restrictions
                weight_restrictions = extract_weight_restriction(criteria)
                if weight_restrictions:
                    result["departments"][dept]["weight_restrictions"].update(
                        weight_restrictions
                    )

                    # Add as an exclusion too
                    weight_text = f"Weight restriction: "
                    if "minimum" in weight_restrictions:
                        weight_text += f"minimum {weight_restrictions['minimum']} kg"
                    if "maximum" in weight_restrictions:
                        if "minimum" in weight_restrictions:
                            weight_text += f", "
                        weight_text += f"maximum {weight_restrictions['maximum']} kg"

                    result["departments"][dept]["exclusions"].append(weight_text)
