#!/usr/bin/env python3
"""
Exclusion Criteria Parser
-------------------------
This utility converts PDF exclusion criteria documents into a structured JSON format
for use by the Transfer Center decision engine.
"""

import os
import json
import logging
import subprocess
import re
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("exclusion_parser")

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "exclusion_criteria.json")

# PDF files to convert
PDF_FILES = {
    "austin": os.path.join(DATA_DIR, "Austin-Transfer-Exclusion-Criteria.pdf"),
    "community": os.path.join(DATA_DIR, "Community-Campus-Exclusion-Criteria-4_2024-v1.pdf"),
}

# Department/specialty mapping for standardization
DEPARTMENT_MAPPING = {
    # General departments
    "administrative": ["administrative", "admin", "general"],
    "nicu": ["nicu", "neonatal", "neonate", "infant", "newborn"],
    "picu": ["picu", "intensive care", "critical care"],
    
    # Medical specialties
    "cardiology": ["cardiology", "cardiac", "heart", "cardiovascular"],
    "pulmonary": ["pulmonary", "respiratory", "breathing", "lung", "airway", "respiratory", "ventilator", "bipap", "cpap"],
    "neurology": ["neurology", "neurological", "brain", "neural", "seizure", "stroke", "eeg"],
    "infectious_disease": ["infectious", "infection", "sepsis", "meningitis"],
    "oncology": ["oncology", "cancer", "tumor", "leukemia", "lymphoma", "malignancy"],
    "hematology": ["hematology", "blood", "anemia", "transfusion", "thrombosis", "hematologic"],
    "endocrinology": ["endocrinology", "endocrine", "diabetes", "thyroid", "dka", "diabetic"],
    "gastroenterology": ["gastroenterology", "gastro", "gi", "liver", "intestinal", "gastrointestinal"],
    "nephrology": ["nephrology", "renal", "kidney", "dialysis", "creatinine"],
    "surgery": ["surgery", "surgical", "operative", "post-op", "operation"],
    "trauma": ["trauma", "injury", "accident", "burn", "fracture"],
    "rheumatology": ["rheumatology", "rheum", "kawasaki", "autoimmune", "arthritis", "mis-c"],
    "psychiatric": ["psychiatric", "psych", "mental health", "behavioral", "psychosis"],
    "maternal": ["maternal", "pregnancy", "pregnant", "birth", "obstetric"],
    "transplant": ["transplant", "rejection", "donor", "graft"],
    "ophthalmology": ["ophthalmology", "eye", "ophthalmic", "ocular", "vision", "ophthalmologic", "retina"],
    "interventional_radiology": ["interventional radiology", "ir", "catheter", "thrombolysis"],
    
    # Other
    "monitoring": ["monitoring", "telemetry", "continuous", "hourly"],
    "weight_restrictions": ["weight", "kg", "weighing"],
    "transport": ["transport", "transportation", "ambulance", "helicopter", "airlift"]
}

# Keywords for better categorization and searching
CONDITION_KEYWORDS = {
    "cardiac": [
        "heart failure", "arrhythmia", "congenital heart", "cardiomyopathy", 
        "hypertension", "cardiovascular", "cardiac", "heart", "cardiology"
    ],
    "respiratory": [
        "respiratory", "breathing", "pulmonary", "lung", "airway", "ventilator",
        "oxygen", "saturation", "intubation", "pneumonia", "asthma", "bronchiolitis"
    ],
    "neurological": [
        "neurological", "brain", "neural", "stroke", "seizure", "epilepsy", 
        "mental status", "consciousness", "meningitis", "encephalopathy"
    ],
    "oncology": [
        "cancer", "oncology", "tumor", "leukemia", "lymphoma", "malignancy",
        "bone marrow", "bmt", "chemotherapy", "radiation"
    ],
    "infectious": [
        "infectious", "infection", "sepsis", "meningitis", "abscess", "cellulitis",
        "bacterial", "viral", "fungal"
    ],
    "trauma": [
        "trauma", "injury", "accident", "fracture", "burn", "wound"
    ],
    "transplant": [
        "transplant", "donor", "graft", "rejection", "immunosuppression"
    ],
    "endocrine": [
        "diabetes", "diabetic", "dka", "thyroid", "endocrine", "hormone", 
        "adrenal", "pituitary", "insulin"
    ],
    "surgery": [
        "surgery", "surgical", "post-op", "operative", "incision", "procedure"
    ],
    "gi": [
        "gastrointestinal", "gi", "liver", "intestinal", "bowel", "biliary",
        "pancreatic", "gallbladder", "hepatic"
    ],
    "renal": [
        "renal", "kidney", "dialysis", "nephrology", "creatinine", "hypertension",
        "electrolyte", "fluid"
    ],
    "hematology": [
        "blood", "anemia", "thrombosis", "transfusion", "hematology", "bleeding",
        "coagulation", "hemoglobin"
    ],
    "pregnancy": [
        "pregnancy", "pregnant", "maternal", "obstetric", "birth", "delivery"
    ],
    "psychiatric": [
        "psychiatric", "mental health", "behavioral", "psychosis", "depression", 
        "anxiety", "suicidal"
    ]
}

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF file using PyPDF2.
    """
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
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""

def identify_department(text: str) -> str:
    """
    Identify the department or specialty associated with a section of text.
    Returns the most likely department name.
    """
    text = text.lower()
    dept_scores = {}
    
    # Score each department based on keyword matches
    for dept, keywords in DEPARTMENT_MAPPING.items():
        score = 0
        for keyword in keywords:
            if keyword in text:
                score += 1
                # Bonus for explicit mentions
                if re.search(rf'\b{keyword}\b', text):
                    score += 2
        if score > 0:
            dept_scores[dept] = score
    
    # Return the department with the highest score, or 'general' if none found
    if dept_scores:
        return max(dept_scores.items(), key=lambda x: x[1])[0]
    return "general"

def identify_conditions(text: str) -> List[str]:
    """
    Identify medical conditions mentioned in the text.
    """
    text = text.lower()
    conditions = set()
    
    for condition, keywords in CONDITION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                conditions.add(condition)
                break
    
    return list(conditions)

def extract_age_restriction(text: str) -> Optional[Dict[str, int]]:
    """
    Extract age restrictions from text.
    Returns a dictionary with keys 'minimum' and/or 'maximum'.
    """
    result = {}
    
    # Look for maximum age limits
    max_age_patterns = [
        r'(?:greater|more|older) than (\d+)(?:\s*(?:years|yo|y\.o\.|year))?',
        r'(?:>|≥|>=|≧)\s*(\d+)(?:\s*(?:years|yo|y\.o\.|year))?',
        r'(\d+)(?:\s*(?:years|yo|y\.o\.|year))? or older'
    ]
    
    for pattern in max_age_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['maximum'] = int(match.group(1))
            break
    
    # Look for minimum age limits
    min_age_patterns = [
        r'(?:less|younger) than (\d+)(?:\s*(?:years|yo|y\.o\.|year))?',
        r'(?:<|≤|<=|≦)\s*(\d+)(?:\s*(?:years|yo|y\.o\.|year))?',
        r'(\d+)(?:\s*(?:years|yo|y\.o\.|year))? or younger'
    ]
    
    for pattern in min_age_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['minimum'] = int(match.group(1))
            break
    
    return result if result else None

def extract_weight_restriction(text: str) -> Optional[Dict[str, float]]:
    """
    Extract weight restrictions from text.
    Returns a dictionary with keys 'minimum' and/or 'maximum'.
    """
    result = {}
    
    # Look for weight limits
    weight_patterns = [
        r'(?:weight|weighing) (?:greater|more|less|<|>|≤|≥|<=|>=|≦|≧) than (\d+(?:\.\d+)?)(?:\s*(?:kg|kilograms|pounds|lbs))',
        r'(?:weight|weighing) (?:<|>|≤|≥|<=|>=|≦|≧)\s*(\d+(?:\.\d+)?)(?:\s*(?:kg|kilograms|pounds|lbs))',
        r'(\d+(?:\.\d+)?)(?:\s*(?:kg|kilograms|pounds|lbs)) or (?:more|less)'
    ]
    
    for pattern in weight_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            weight = float(match.group(1))
            if 'less' in text.lower() or '<' in text:
                result['maximum'] = weight
            else:
                result['minimum'] = weight
            # Convert to kg if in pounds
            if 'pound' in text.lower() or 'lbs' in text.lower():
                if 'maximum' in result:
                    result['maximum'] *= 0.453592
                if 'minimum' in result:
                    result['minimum'] *= 0.453592
            break
    
    return result if result else None

def parse_austin_exclusions(text: str) -> Dict[str, Any]:
    """
    Parse the Austin campus exclusion criteria PDF.
    """
    result = {
        "display_name": "Austin Transfer Exclusion Criteria",
        "departments": {},
        "general_exclusions": [],
        "age_restrictions": None,
        "weight_restrictions": None
    }
    
    # Extract major sections
    sections = re.split(r'\n\s*(?=\w+\s+(?:Campus|Exclusions|Review|Transfer))', text)
    
    for section in sections:
        if not section.strip():
            continue
        
        # Look for bullet points or numbered lists
        bullet_items = re.findall(r'(?:•|\*|\-|\u2022|\uf0b7)\s*(.*?)(?=(?:•|\*|\-|\u2022|\uf0b7|\n\n|\Z))', section, re.DOTALL)
        if not bullet_items:
            # Try numbered items
            bullet_items = re.findall(r'(?:\d+\.|\(\d+\))\s*(.*?)(?=(?:\d+\.|\(\d+\)|\n\n|\Z))', section, re.DOTALL)
        
        # If still no items found, treat the whole section as one item
        if not bullet_items:
            bullet_items = [section.strip()]
        
        # Get the section title
        section_title = section.split('\n')[0].strip()
        department = identify_department(section_title)
        
        for item in bullet_items:
            item = item.strip()
            if not item:
                continue
            
            # Check for general criteria vs. department-specific
            if "Administrative Review" in section or "general" in department:
                result["general_exclusions"].append(item)
                
                # Check for age restrictions
                age_restrictions = extract_age_restriction(item)
                if age_restrictions:
                    result["age_restrictions"] = age_restrictions
                
                # Check for weight restrictions
                weight_restrictions = extract_weight_restriction(item)
                if weight_restrictions:
                    result["weight_restrictions"] = weight_restrictions
            else:
                # Department-specific exclusion
                dept = identify_department(item) if "general" in department else department
                
                if dept not in result["departments"]:
                    result["departments"][dept] = {
                        "exclusions": [],
                        "conditions": set()
                    }
                
                result["departments"][dept]["exclusions"].append(item)
                
                # Add conditions
                conditions = identify_conditions(item)
                result["departments"][dept]["conditions"].update(conditions)
    
    # Convert condition sets to lists for JSON serialization
    for dept in result["departments"]:
        result["departments"][dept]["conditions"] = list(result["departments"][dept]["conditions"])
    
    return result

def parse_community_exclusions(text: str) -> Dict[str, Any]:
    """
    Parse the Community campus exclusion criteria PDF.
    Handles the complex table structure with columns for different types of exclusions.
    """
    result = {
        "display_name": "Texas Children's Hospital Community Sites Admission Exclusion Criteria",
        "departments": {},
        "general_exclusions": [],
        "age_restrictions": None,
        "weight_restrictions": None,
        "campus_notes": {}
    }
    
    # First, extract the overview section for general information
    overview_match = re.search(r'Overview of Community Sites:([\s\S]*?)(?=\n\n)', text)
    if overview_match:
        result["campus_notes"]["overview"] = overview_match.group(1).strip()
    
    # Weight restriction typically mentioned for infants
    weight_match = re.search(r'Infants weighing <(\d+\.?\d*) kg', text)
    if weight_match:
        result["weight_restrictions"] = {"minimum": float(weight_match.group(1))}
    
    # Try to extract the table data by using the Problem/Diagnosis headers as markers
    # This will help us identify sections of the document
    table_sections = re.split(r'\s*Problem/Diagnosis\s*', text)
    if len(table_sections) > 1:
        # Skip the first section (before the first Problem/Diagnosis header)
        table_sections = table_sections[1:]
        
        for section in table_sections:
            # Process each section of the table
            process_community_table_section(section, result)
    
    # Process special sections that might be outside the main table format
    process_special_sections(text, result)
    
    # Clean up the exclusions - remove duplicates and invalid entries
    clean_exclusion_data(result)
    
    # Convert condition sets to lists for JSON serialization
    for dept in result["departments"]:
        result["departments"][dept]["conditions"] = list(result["departments"][dept]["conditions"])
    
    return result

def process_community_table_section(section: str, result: Dict[str, Any]) -> None:
    """
    Process a section of the Community campus exclusion table.
    
    Args:
        section: Text of a section from the table
        result: Result dictionary to update
    """
    # Identify which department this section belongs to by looking at the first few lines
    header_lines = section.split('\n', 3)[0:2]  # Get first two lines for department identification
    header_text = ' '.join(header_lines)
    
    # Detect department from the header text
    department = identify_department(header_text)
    if not department or department == 'general':
        # Try to extract from the section title which often appears at the start
        match = re.search(r'^\s*([\w\s-]+?)\s*(?:\n|$)', section)
        if match:
            dept_name = match.group(1).strip()
            if len(dept_name) > 3:  # Avoid very short strings
                department = identify_department(dept_name)
    
    # If still no valid department, fall back to general
    if not department or department == 'general':
        department = "other"
    
    # Initialize department if not present
    if department not in result["departments"]:
        result["departments"][department] = {
            "exclusions": [],
            "conditions": set(identify_conditions(section))
        }
    else:
        result["departments"][department]["conditions"].update(identify_conditions(section))
    
    # Extract exclusion items from the different columns
    # We're looking for lines that indicate exclusions
    
    # AC Exclusion column
    ac_exclusions = re.findall(r'(?:^|\n)\s*(?:•|\*|\-|\u2022|\uf0b7)?\s*([^\n]+?)\s+(?:X|✓)\s+(?:AC Exclusion)', section, re.DOTALL)
    
    # Community Exclusion column
    community_exclusions = re.findall(r'(?:^|\n)\s*(?:•|\*|\-|\u2022|\uf0b7)?\s*([^\n]+?)\s+(?:X|✓)\s+(?:Community)', section, re.DOTALL)
    
    # Also try to find bullet points with exclusions
    bullet_exclusions = re.findall(r'(?:^|\n)\s*(?:•|\*|\-|\u2022|\uf0b7)\s*([^\n•\*\-\u2022\uf0b7]+)', section)
    
    # Combine all found exclusions
    all_exclusions = ac_exclusions + community_exclusions + bullet_exclusions
    
    # Process each exclusion item
    for item in all_exclusions:
        item = item.strip()
        # Skip empty items or headers
        if not item or item.lower() in ['acute care', 'decision by', 'ac exclusion', 'community', 'picu accept']:
            continue
        
        # Skip very short items (likely column headers or fragments)
        if len(item) < 5:
            continue
        
        # Skip items that appear to be column indicators
        if re.match(r'^[X✓]+$', item):
            continue
            
        # Clean up the item - remove trailing column indicators
        clean_item = re.sub(r'\s+(?:X|✓)\s*$', '', item)
        
        # Add to the department's exclusions if not already present
        if clean_item not in result["departments"][department]["exclusions"]:
            result["departments"][department]["exclusions"].append(clean_item)

def process_special_sections(text: str, result: Dict[str, Any]) -> None:
    """
    Process special sections in the Community PDF that might be outside the main table.
    
    Args:
        text: Full text of the PDF
        result: Result dictionary to update
    """
    # Extract specific department sections by looking for headers
    departments = {
        "cardiology": "Cardiology",
        "nicu": "Neonatology",
        "trauma": "Trauma",
        "oncology": "Hematology/Oncology",
        "neurology": "Neurologic",
        "respiratory": "Respiratory",
        "psychiatric": "Psychiatric",
        "endocrinology": "Endocrine"
    }
    
    for dept_key, dept_name in departments.items():
        # Find the section for this department
        pattern = f"\\b{dept_name}\\b([\\s\\S]*?)(?=\\n\\s*\\n|\\Z)"
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            section_text = match.group(1).strip()
            
            # Ensure the department exists in the result
            if dept_key not in result["departments"]:
                result["departments"][dept_key] = {
                    "exclusions": [],
                    "conditions": set(identify_conditions(section_text))
                }
            else:
                result["departments"][dept_key]["conditions"].update(identify_conditions(section_text))
            
            # Extract bullet points or list items
            items = re.findall(r'(?:•|\*|\-|\u2022|\uf0b7|\d+\.|\(\d+\))\s*([^\n•\*\-\u2022\uf0b7\d\(\)]+)', section_text)
            
            for item in items:
                item = item.strip()
                if len(item) > 5 and item not in result["departments"][dept_key]["exclusions"]:
                    result["departments"][dept_key]["exclusions"].append(item)

def clean_exclusion_data(result: Dict[str, Any]) -> None:
    """
    Clean up the extracted exclusion data by removing duplicates,
    irrelevant entries, and correcting common parsing issues.
    
    Args:
        result: Result dictionary to clean
    """
    # Words that indicate an item is not an actual exclusion criterion
    non_exclusion_indicators = [
        "acute care", "decision by", "ac exclusion", "picu accept", "community exclusion",
        "x", "✓", "accept", "last reviewed", "reviewed by", "reviewed:", "cmo", "west campus",
        "woodlands campus", "problem/diagnosis", "van zandt", "leaming", "team", "clinical team",
        "appendix", "sop", "document", "floor", "includes", "criteria", "guidelines", "score"
    ]
    
    # Names to filter out (team member names that appear in the PDF footer)
    name_patterns = [
        r"(?:by|with)\s+[A-Z][a-z]+\s+[A-Z][a-z]+",
        r"\w+\s+[A-Z][a-z]+\s+\([A-Z]{2,}\)",
        r"[A-Z][a-z]+\s+[A-Z][a-z]+\s+\([A-Z]{2,}\)"
    ]
    
    # Process each department
    departments_to_remove = []
    for dept, dept_data in result["departments"].items():
        # Check for fragmented exclusions that should be joined
        exclusions_to_join = {}
        joined_items = set()
        
        # First pass - identify fragments that should be joined
        for i, item in enumerate(dept_data["exclusions"]):
            # Check if this item ends with common fragment indicators
            if item.endswith(("require", "requiring", "with", "without", "and", "or", "including", "on")):
                # This is likely a fragment - store it for joining
                exclusions_to_join[i] = item
                joined_items.add(i)
            
            # Check the next item (if available) to see if it starts lowercase or with a continuation indicator
            if i + 1 < len(dept_data["exclusions"]):
                next_item = dept_data["exclusions"][i + 1]
                if (next_item and next_item[0].islower()) or next_item.startswith(("with", "without", "or", "and", "requiring")):
                    # Next item is a continuation - include this one for joining
                    if i not in exclusions_to_join:
                        exclusions_to_join[i] = item
                        joined_items.add(i)
                    # Mark the next item as part of a join operation
                    joined_items.add(i + 1)
        
        # Join the fragments
        joined_exclusions = []
        current_join = ""
        for i, item in enumerate(dept_data["exclusions"]):
            if i in joined_items:
                if i in exclusions_to_join:
                    # Start of a join operation
                    if current_join:
                        # End the previous join if there was one
                        joined_exclusions.append(current_join.strip())
                    current_join = item
                else:
                    # Continuation of a join
                    current_join += " " + item
            else:
                # Not part of a join - add any previous join and then this item
                if current_join:
                    joined_exclusions.append(current_join.strip())
                    current_join = ""
                joined_exclusions.append(item)
        
        # Add the final join if there is one
        if current_join:
            joined_exclusions.append(current_join.strip())
        
        # Filter out non-exclusion entries
        filtered_exclusions = []
        for item in joined_exclusions:
            # Convert to lowercase for checking
            item_lower = item.lower()
            
            # Skip items that match non-exclusion indicators
            if any(indicator in item_lower for indicator in non_exclusion_indicators):
                continue
                
            # Skip items that match name patterns
            if any(re.search(pattern, item, re.IGNORECASE) for pattern in name_patterns):
                continue
                
            # Skip items that are just column headers or short codes
            if item_lower in ["x", "✓", "y", "n", "yes", "no", "dx", "tx", "cc", "ac", "wc", "wl"]:
                continue
                
            # Skip items that are too short to be meaningful
            if len(item) < 10:  # Increased from 5 to filter out more short fragments
                continue
                
            # Skip items that are just numbers, single letters, or dates
            if re.match(r'^[\d\s]+$', item) or re.match(r'^[a-zA-Z]$', item) or re.match(r'^\d{1,2}/\d{4}$', item):
                continue
            
            # Skip items that are page numbers or section markers
            if re.match(r'^\d+$', item) or re.match(r'^[A-Z]\.$', item):
                continue
            
            # Clean up any extra whitespace or linebreaks
            cleaned_item = re.sub(r'\s+', ' ', item).strip()
            
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
        if (not any(indicator in item_lower for indicator in non_exclusion_indicators) and 
            not any(re.search(pattern, item, re.IGNORECASE) for pattern in name_patterns) and
            len(item) >= 10):
            cleaned_item = re.sub(r'\s+', ' ', item).strip()
            if cleaned_item and cleaned_item not in general_exclusions:
                general_exclusions.append(cleaned_item)
    
    result["general_exclusions"] = general_exclusions

def convert_pdfs_to_json() -> Dict[str, Any]:
    """
    Convert all PDF files to a structured JSON format.
    """
    result = {
        "version": "1.0",
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "campuses": {}
    }
    
    # Process Austin exclusions
    if os.path.exists(PDF_FILES["austin"]):
        logger.info(f"Processing Austin exclusion criteria from {PDF_FILES['austin']}")
        austin_text = extract_text_from_pdf(PDF_FILES["austin"])
        if austin_text:
            result["campuses"]["austin"] = parse_austin_exclusions(austin_text)
            logger.info(f"Extracted {len(result['campuses']['austin']['departments'])} departments with exclusion criteria from Austin")
        else:
            logger.error("Failed to extract text from Austin PDF")
    else:
        logger.warning(f"Austin PDF file not found: {PDF_FILES['austin']}")
    
    # Process Community exclusions
    if os.path.exists(PDF_FILES["community"]):
        logger.info(f"Processing Community exclusion criteria from {PDF_FILES['community']}")
        community_text = extract_text_from_pdf(PDF_FILES["community"])
        if community_text:
            result["campuses"]["community"] = parse_community_exclusions(community_text)
            logger.info(f"Extracted {len(result['campuses']['community']['departments'])} departments with exclusion criteria from Community")
        else:
            logger.error("Failed to extract text from Community PDF")
    else:
        logger.warning(f"Community PDF file not found: {PDF_FILES['community']}")
    
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
