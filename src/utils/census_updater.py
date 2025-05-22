"""
Census updater utility for the Transfer Center application.

This script reads the current_census.csv file and updates the hospital campuses
data with the latest bed availability information.
"""
import os
import json
import csv
import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

def read_census_data(census_file_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Read census data from CSV file and organize by campus ID.
    
    Args:
        census_file_path: Path to the census CSV file
        
    Returns:
        Dictionary with campus_id as key and census data as value
    """
    if not os.path.exists(census_file_path):
        logger.error(f"Census file not found: {census_file_path}")
        return {}
    
    campus_census = defaultdict(lambda: {
        "general_beds": {"total": 0, "available": 0},
        "icu_beds": {"total": 0, "available": 0},
        "nicu_beds": {"total": 0, "available": 0},
        "specialized_units": defaultdict(list)
    })
    
    try:
        with open(census_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                campus_id = row.get('campus_id')
                if not campus_id:
                    continue
                
                unit_type = row.get('unit_type', 'general')
                total_beds = int(row.get('total_beds', 0))
                available_beds = int(row.get('available_beds', 0))
                unit_name = row.get('unit_name', '')
                unit_id = row.get('unit_id', '')
                
                # Aggregate bed counts by unit type
                if unit_type == 'general':
                    campus_census[campus_id]['general_beds']['total'] += total_beds
                    campus_census[campus_id]['general_beds']['available'] += available_beds
                elif unit_type == 'icu':
                    campus_census[campus_id]['icu_beds']['total'] += total_beds
                    campus_census[campus_id]['icu_beds']['available'] += available_beds
                elif unit_type == 'nicu':
                    campus_census[campus_id]['nicu_beds']['total'] += total_beds
                    campus_census[campus_id]['nicu_beds']['available'] += available_beds
                
                # Track specialized units (oncology, pulmonary, etc.)
                specialization = detect_specialization(unit_name, unit_id)
                if specialization:
                    campus_census[campus_id]['specialized_units'][specialization].append({
                        'unit_id': unit_id,
                        'unit_name': unit_name,
                        'total_beds': total_beds,
                        'available_beds': available_beds
                    })
                    
    except Exception as e:
        logger.error(f"Error reading census data: {str(e)}")
        return {}
    
    return campus_census

def detect_specialization(unit_name: str, unit_id: str) -> Optional[str]:
    """
    Detect specialization of a unit based on its name or ID.
    
    Args:
        unit_name: Name of the unit
        unit_id: ID of the unit
        
    Returns:
        Specialization type or None if no specialization detected
    """
    name_lower = unit_name.lower()
    id_lower = unit_id.lower()
    
    specialization_keywords = {
        'oncology': ['oncology', 'hemonc', 'cancer', 'bmt', 'bone marrow'],
        'cardiology': ['cardiology', 'cardiac', 'cardio', 'cvicu', 'heart'],
        'neurology': ['neurology', 'neuro', 'brain', 'spine'],
        'pulmonary': ['pulmonary', 'respiratory', 'lung'],
        'surgery': ['surgery', 'surgical', 'post-op'],
        'trauma': ['trauma'],
        'pediatric_icu': ['picu'],
        'neonatal': ['nicu', 'newborn', 'neonatal'],
        'women': ['women', 'labor', 'delivery', 'l&d', 'mother', 'maternal'],
        'rehabilitation': ['rehab', 'rehabilitation'],
        'adolescent': ['adolescent', 'teen', 'adol'],
        'endocrinology': ['endocrinology', 'endo', 'diabetes'],
    }
    
    for specialty, keywords in specialization_keywords.items():
        if any(keyword in name_lower for keyword in keywords) or any(keyword in id_lower for keyword in keywords):
            return specialty
    
    return None

def update_hospital_campuses(campus_file_path: str, census_data: Dict[str, Dict[str, Any]]) -> bool:
    """
    Update hospital campuses data with the latest census information.
    
    Args:
        campus_file_path: Path to the hospital campuses JSON file
        census_data: Dictionary with campus_id as key and census data as value
        
    Returns:
        True if successful, False otherwise
    """
    if not os.path.exists(campus_file_path):
        logger.error(f"Hospital campuses file not found: {campus_file_path}")
        return False
    
    try:
        with open(campus_file_path, 'r', encoding='utf-8') as f:
            campuses = json.load(f)
        
        # Update each campus with the latest census data
        for campus in campuses:
            campus_id = campus.get('campus_id')
            if campus_id in census_data:
                # Update bed census
                if 'bed_census' not in campus:
                    campus['bed_census'] = {}
                
                campus['bed_census']['total_beds'] = sum([
                    census_data[campus_id]['general_beds']['total'],
                    census_data[campus_id]['icu_beds']['total'],
                    census_data[campus_id]['nicu_beds']['total']
                ])
                campus['bed_census']['available_beds'] = sum([
                    census_data[campus_id]['general_beds']['available'],
                    census_data[campus_id]['icu_beds']['available'],
                    census_data[campus_id]['nicu_beds']['available']
                ])
                campus['bed_census']['icu_beds_total'] = census_data[campus_id]['icu_beds']['total']
                campus['bed_census']['icu_beds_available'] = census_data[campus_id]['icu_beds']['available']
                campus['bed_census']['nicu_beds_total'] = census_data[campus_id]['nicu_beds']['total']
                campus['bed_census']['nicu_beds_available'] = census_data[campus_id]['nicu_beds']['available']
                
                # Add specialized unit information
                campus['specialized_units'] = dict(census_data[campus_id]['specialized_units'])
        
        # Write updated data back to the file
        with open(campus_file_path, 'w', encoding='utf-8') as f:
            json.dump(campuses, f, indent=2)
        
        logger.info(f"Successfully updated hospital campuses data with latest census information")
        return True
        
    except Exception as e:
        logger.error(f"Error updating hospital campuses data: {str(e)}")
        return False

def update_census(census_file_path: str = None, campus_file_path: str = None) -> bool:
    """
    Main function to update the hospital campuses with current census data.
    
    Args:
        census_file_path: Path to the census CSV file
        campus_file_path: Path to the hospital campuses JSON file
        
    Returns:
        True if successful, False otherwise
    """
    # Use default paths if not provided
    if not census_file_path:
        census_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                       'data', 'current_census.csv')
    
    if not campus_file_path:
        campus_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                       'data', 'sample_hospital_campuses.json')
    
    # Read census data and update hospital campuses
    census_data = read_census_data(census_file_path)
    if not census_data:
        return False
    
    return update_hospital_campuses(campus_file_path, census_data)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Update census
    success = update_census()
    print(f"Census update {'successful' if success else 'failed'}")
