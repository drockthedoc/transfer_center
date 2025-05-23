"""
Main parser module for the exclusion criteria parser.

This module contains the main functions for converting PDF exclusion criteria to JSON format.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

from src.utils.exclusion.constants import OUTPUT_FILE, PDF_FILES
from src.utils.exclusion.extractors import extract_text_from_pdf
from src.utils.exclusion.processors import (
    parse_austin_exclusions,
    parse_community_exclusions,
)
from src.utils.exclusion.cleaners import clean_exclusion_data

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("exclusion_parser")


def convert_pdfs_to_json() -> Dict[str, Any]:
    """
    Convert all PDF files to a structured JSON format.
    """
    result = {
        "version": "1.0",
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "campuses": {},
    }

    # Process Austin exclusions
    if os.path.exists(PDF_FILES["austin"]):
        logger.info(f"Processing Austin exclusion criteria from {PDF_FILES['austin']}")
        austin_text = extract_text_from_pdf(PDF_FILES["austin"])
        if austin_text:
            result["campuses"]["austin"] = parse_austin_exclusions(austin_text)
            # Clean the extracted data
            clean_exclusion_data(result["campuses"]["austin"])
            logger.info(
                f"Extracted {len(result['campuses']['austin']['departments'])} departments with exclusion criteria from Austin"
            )
        else:
            logger.error("Failed to extract text from Austin PDF")
    else:
        logger.warning(f"Austin PDF file not found: {PDF_FILES['austin']}")

    # Process Community exclusions
    if os.path.exists(PDF_FILES["community"]):
        logger.info(
            f"Processing Community exclusion criteria from {PDF_FILES['community']}"
        )
        community_text = extract_text_from_pdf(PDF_FILES["community"])
        if community_text:
            result["campuses"]["community"] = parse_community_exclusions(community_text)
            # Clean the extracted data
            clean_exclusion_data(result["campuses"]["community"])
            logger.info(
                f"Extracted {len(result['campuses']['community']['departments'])} departments with exclusion criteria from Community"
            )
        else:
            logger.error("Failed to extract text from Community PDF")
    else:
        logger.warning(f"Community PDF file not found: {PDF_FILES['community']}")

    return result


def save_json(data: Dict[str, Any], output_path: str) -> None:
    """
    Save the extracted data to a JSON file.
    """
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved exclusion criteria to {output_path}")


def main():
    """
    Main function to run the conversion process.
    """
    logger.info("Starting exclusion criteria conversion")

    # Convert PDFs to JSON
    exclusion_data = convert_pdfs_to_json()

    # Save to file
    save_json(exclusion_data, OUTPUT_FILE)

    logger.info("Conversion complete")
    return exclusion_data
