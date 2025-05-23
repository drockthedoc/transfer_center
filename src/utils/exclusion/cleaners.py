"""
Cleaners for the exclusion criteria parser.

This module contains functions for cleaning and standardizing the extracted exclusion data.
"""

import re
from typing import Dict, List, Any, Set


def clean_exclusion_data(result: Dict[str, Any]) -> None:
    """
    Clean up the extracted exclusion data by removing duplicates,
    irrelevant entries, and correcting common parsing issues.

    Args:
        result: Result dictionary to clean
    """
    # Indicators of non-exclusion content
    non_exclusion_indicators = [
        "please", "thank", "contact", "refer to", "see ", "available", "approved",
        "accepted", "allowed", "permitted", "recommended", "guidelines", "policy",
        "procedure", "inclusion", "criteria for", "criteria:", "note:",
        "admission", "transfer", "instructions"
    ]
    
    # Patterns for names, headings, etc. to filter out
    name_patterns = [
        r"^Dr\.\s+[A-Z][a-z]+",
        r"^[A-Z][a-z]+\s+[A-Z][a-z]+,\s+(?:MD|RN|DO|PhD)",
        r"^(?:MD|RN|DO|PhD):",
        r"^(?:Page \d+|Section \d+|Updated:)",
        r"^\d{1,2}/\d{1,2}/\d{2,4}",
        r"^(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
    ]
    
    # Clean each department's exclusions
    departments_to_remove = []
    for dept, dept_data in result["departments"].items():
        filtered_exclusions = []
        for item in dept_data["exclusions"]:
            # Skip items that aren't exclusions
            item_lower = item.lower()
            if any(indicator in item_lower for indicator in non_exclusion_indicators):
                continue
                
            # Skip items matching name patterns
            if any(re.search(pattern, item, re.IGNORECASE) for pattern in name_patterns):
                continue
                
            # Skip very short items (likely parsing artifacts)
            if len(item) < 10:
                continue
                
            # Skip number-only items or single letters (likely section markers)
            if (
                re.match(r"^[\d\s]+$", item)
                or re.match(r"^[a-zA-Z]$", item)
                or re.match(r"^\d{1,2}/\d{4}$", item)
            ):
                continue

            # Skip items that are page numbers or section markers
            if re.match(r"^\d+$", item) or re.match(r"^[A-Z]\.$", item):
                continue

            # Clean up any extra whitespace or linebreaks
            cleaned_item = re.sub(r"\s+", " ", item).strip()

            # Add the cleaned item if not already present and not empty
            if cleaned_item and cleaned_item not in filtered_exclusions:
                filtered_exclusions.append(cleaned_item)

        # Update the exclusions with the filtered list
        dept_data["exclusions"] = filtered_exclusions

        # If a department has no exclusions after filtering, mark it for removal
        if not filtered_exclusions and not dept_data["conditions"]:
            departments_to_remove.append(dept)

    # Remove empty departments
    for dept in departments_to_remove:
        del result["departments"][dept]

    # Clean general exclusions with the same approach
    general_exclusions = []
    for item in result["general_exclusions"]:
        item_lower = item.lower()
        if (
            not any(indicator in item_lower for indicator in non_exclusion_indicators)
            and not any(
                re.search(pattern, item, re.IGNORECASE) for pattern in name_patterns
            )
            and len(item) >= 10
        ):
            cleaned_item = re.sub(r"\s+", " ", item).strip()
            if cleaned_item and cleaned_item not in general_exclusions:
                general_exclusions.append(cleaned_item)

    result["general_exclusions"] = general_exclusions
