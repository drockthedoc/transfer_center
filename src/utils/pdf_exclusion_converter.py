#!/usr/bin/env python3
"""
PDF Exclusion Criteria Converter
--------------------------------
This utility converts PDF exclusion criteria documents into JSON format
for use by the Transfer Center decision engine.
"""

import os
import json
import logging
import subprocess
import re
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("pdf_exclusion_converter")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "exclusion_criteria.json")

# PDF files to convert
PDF_FILES = {
    "austin": os.path.join(DATA_DIR, "Austin-Transfer-Exclusion-Criteria.pdf"),
    "community": os.path.join(DATA_DIR, "Community-Campus-Exclusion-Criteria-4_2024-v1.pdf"),
}

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF file using the pdftotext command-line utility.
    Falls back to simpler methods if pdftotext is not available.
    """
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", pdf_path, "-"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("pdftotext not available, trying alternate method")
        # Try to use python-based extraction if pdftotext fails
        try:
            import PyPDF2
            with open(pdf_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except ImportError:
            logger.error("PyPDF2 not available. Please install with 'pip install PyPDF2'")
            return ""

def parse_exclusion_criteria(text: str) -> List[Dict[str, Any]]:
    """
    Parse the extracted text to identify exclusion criteria.
    This function uses pattern matching to extract structured data.
    """
    criteria = []
    
    # Split by common section markers or numbered items
    # This is a simplified approach and may need refinement based on actual PDF structure
    sections = re.split(r'\n\s*\d+[\.|\)]\s+', text)
    
    for section in sections:
        if not section.strip():
            continue
        
        # Try to identify category/subcategory
        lines = section.strip().split('\n')
        category = lines[0].strip() if lines else ""
        
        # Check for age restrictions
        age_match = re.search(r'(\d+)\s*(?:years|yo|y\.o\.|year)', section, re.IGNORECASE)
        age_limit = int(age_match.group(1)) if age_match else None
        
        # Check for weight restrictions
        weight_match = re.search(r'(\d+)\s*(?:kg|kilograms|pounds|lbs)', section, re.IGNORECASE)
        weight_limit = int(weight_match.group(1)) if weight_match else None
        
        # Look for medical conditions
        conditions = []
        condition_keywords = [
            "trauma", "cardiac", "neurological", "respiratory", "oncology", 
            "infectious", "sepsis", "burn", "stroke", "pregnancy"
        ]
        
        for keyword in condition_keywords:
            if re.search(r'\b' + keyword + r'\b', section, re.IGNORECASE):
                conditions.append(keyword.lower())
        
        criteria.append({
            "category": category,
            "full_text": section.strip(),
            "age_limit": age_limit,
            "weight_limit": weight_limit,
            "conditions": conditions,
            "keywords": [word.lower() for word in re.findall(r'\b\w{4,}\b', section) 
                        if word.lower() not in ["with", "that", "this", "from", "they", "have", "will"]]
        })
    
    return criteria

def convert_pdfs_to_json() -> Dict[str, List[Dict[str, Any]]]:
    """
    Convert all PDF files to a single JSON structure.
    """
    result = {}
    
    for campus_key, pdf_path in PDF_FILES.items():
        if not os.path.exists(pdf_path):
            logger.warning(f"PDF file not found: {pdf_path}")
            continue
        
        logger.info(f"Processing {campus_key} exclusion criteria from {pdf_path}")
        
        # Extract text from PDF
        text = extract_text_from_pdf(pdf_path)
        if not text:
            logger.error(f"Failed to extract text from {pdf_path}")
            continue
        
        # Parse exclusion criteria
        criteria = parse_exclusion_criteria(text)
        logger.info(f"Extracted {len(criteria)} exclusion criteria from {campus_key}")
        
        # Add to result
        result[campus_key] = criteria
    
    return result

def save_json(data: Dict[str, Any], output_path: str) -> None:
    """
    Save the extracted data to a JSON file.
    """
    with open(output_path, 'w') as f:
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

if __name__ == "__main__":
    main()
