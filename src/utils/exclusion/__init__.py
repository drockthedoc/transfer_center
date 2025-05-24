"""
Exclusion Criteria Parser Package

This package contains modules for parsing and processing exclusion criteria
from various document formats into structured data for the Transfer Center.
"""

from src.utils.exclusion.cleaners import clean_exclusion_data
from src.utils.exclusion.extractors import (
    extract_age_restriction,
    extract_text_from_pdf,
    extract_weight_restriction,
    identify_conditions,
    identify_department,
)
from src.utils.exclusion.parser import convert_pdfs_to_json, main
from src.utils.exclusion.processors import (
    parse_austin_exclusions,
    parse_community_exclusions,
    process_community_table_section,
    process_special_sections,
)
