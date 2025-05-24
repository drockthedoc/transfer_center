"""Census updater utility for the Transfer Center application.

This script reads the current_census.csv file and updates the hospital campuses
data with the latest bed availability information.
"""

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


def _process_census_row(
    row: Dict[str, str],
    campus_data: Dict[str, Any],
    processed_units: set,
    stats: Dict[str, Any]
) -> None:
    """Process a single row of census data.

    Args:
        row: Dictionary containing row data
        campus_data: Dictionary to store processed campus data
        processed_units: Set of already processed units to detect duplicates
        stats: Dictionary to store processing statistics
    """
    try:
        campus_id = row["CampusID"].strip()
        unit_name = row["Unit"].strip()
        unit_key = f"{campus_id}:{unit_name}"
        if unit_key in processed_units:
            stats["duplicate_count"] += 1
            return
        processed_units.add(unit_key)
        stats["campus_ids"].add(campus_id)

        # Initialize campus data if not exists
        if campus_id not in campus_data:
            campus_data[campus_id] = {
                "general_beds": {"available": 0, "total": 0},
                "icu_beds": {"available": 0, "total": 0},
                "nicu_beds": {"available": 0, "total": 0},
                "specialized_units": {},
            }

        # Get bed counts
        available = int(float(row.get("AvailableBeds", 0)))
        total = int(float(row.get("TotalBeds", 0)))

        # Update statistics
        stats["total_available"] += available
        stats["total_capacity"] += total
        stats["min_available"] = min(stats["min_available"], available)
        stats["max_available"] = max(stats["max_available"], available)

        # Categorize unit type and update counts
        unit_name_lower = unit_name.lower()
        if "icu" in unit_name_lower or "intensive" in unit_name_lower:
            bed_type = "icu"
            campus_data[campus_id]["icu_beds"]["available"] += available
            campus_data[campus_id]["icu_beds"]["total"] += total
        elif "nicu" in unit_name_lower or "neonatal" in unit_name_lower:
            bed_type = "nicu"
            campus_data[campus_id]["nicu_beds"]["available"] += available
            campus_data[campus_id]["nicu_beds"]["total"] += total
        else:
            bed_type = "general"
            campus_data[campus_id]["general_beds"]["available"] += available
            campus_data[campus_id]["general_beds"]["total"] += total

        stats["bed_type_counts"][bed_type] += 1
        stats["unit_types"].add(unit_name)

        # Handle specialized units
        if "Specialization" in row and row["Specialization"].strip():
            spec = row["Specialization"].strip()
            stats["specializations"].add(spec)

            if unit_name not in campus_data[campus_id]["specialized_units"]:
                campus_data[campus_id]["specialized_units"][unit_name] = {
                    "specialization": spec,
                    "available_beds": available,
                    "total_beds": total,
                }

    except (ValueError, KeyError) as e:
        stats["error_count"] += 1
        logger.warning("Error processing row: %s - %s", row, str(e))


def read_census_data(census_file_path: str) -> Dict[str, Dict[str, Any]]:
    """Read and process census data from a CSV file.

    Args:
        census_file_path: Path to the census CSV file

    Returns:
        Dictionary mapping campus IDs to their census data, or empty dict on error.
        Each campus has general, ICU, and NICU bed counts, plus specialized units.
    """
    census_file = Path(census_file_path)
    if not census_file.exists():
        logger.error("Census file not found: %s", census_file_path)
        return {}

    campus_data = {}
    required_columns = ["CampusID", "Unit", "AvailableBeds", "TotalBeds"]

    # Initialize statistics
    stats = {
        "processed_units": set(),
        "duplicate_count": 0,
        "error_count": 0,
        "row_count": 0,
        "campus_ids": set(),
        "unit_types": set(),
        "specializations": set(),
        "min_available": float("inf"),
        "max_available": float("-inf"),
        "total_available": 0,
        "total_capacity": 0,
        "bed_type_counts": defaultdict(int),
    }

    try:
        with open(census_file, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            # Validate required columns
            missing_columns = [
                col for col in required_columns
                if col not in reader.fieldnames
            ]
            if missing_columns:
                logger.error("Missing required columns: %s", ", ".join(missing_columns))
                return {}

            # Process each row
            for row in reader:
                stats["row_count"] += 1
                _process_census_row(row, campus_data, stats["processed_units"], stats)

        # Log processing summary
        logger.info(
            "Processed %d rows with %d errors and %d duplicates",
            stats["row_count"],
            stats["error_count"],
            stats["duplicate_count"],
        )
        logger.info(
            "Found %d unique campuses with %d unit types and %d specializations",
            len(stats["campus_ids"]),
            len(stats["unit_types"]),
            len(stats["specializations"]),
        )
        logger.info(
            "Bed distribution - General: %d, ICU: %d, NICU: %d, Other: %d",
            stats["bed_type_counts"]["general"],
            stats["bed_type_counts"]["icu"],
            stats["bed_type_counts"]["nicu"],
            stats["bed_type_counts"]["other"],
        )
        if stats["row_count"] > 0:
            logger.info(
                "Bed availability - Min: %d, Max: %d, Avg: %.2f, Capacity: %d",
                stats["min_available"] if stats["min_available"] != float("inf") else 0,
                stats["max_available"]
                if stats["max_available"] != float("-inf")
                else 0,
                stats["total_available"] / stats["row_count"]
                if stats["row_count"] > 0
                else 0,
                stats["total_capacity"],
            )

        return campus_data

    except (IOError, csv.Error) as e:
        logger.error("Error reading census file: %s", str(e))
        return {}


def _process_test_data(test_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Process test data into standardized census format.

    Converts test data into the standard census data structure with all required fields.

    Args:
        test_data: Raw test data with campus information

    Returns:
        Standardized census data with consistent structure:
        {
            "campus_id": {
                "general_beds": {"total": int, "available": int},
                "icu_beds": {"total": int, "available": int},
                "nicu_beds": {"total": int, "available": int},
                "specialized_units": Dict[str, Any]
            }
        }
    """
    processed_data = {}
    bed_categories = ("general_beds", "icu_beds", "nicu_beds")

    for campus_id, campus_data in test_data.items():
        # Initialize with default values for all bed types
        processed_data[campus_id] = {
            bed_type: {"total": 0, "available": 0} for bed_type in bed_categories
        }
        processed_data[campus_id]["specialized_units"] = {}

        # Update with actual data if available
        for bed_type in bed_categories:
            if bed_type in campus_data:
                processed_data[campus_id][bed_type].update(campus_data[bed_type])

        # Add specialized units if present
        if "specialized_units" in campus_data:
            processed_data[campus_id]["specialized_units"].update(
                campus_data["specialized_units"]
            )

    return processed_data


def _log_census_summary(campus_data: Dict[str, Any]) -> None:
    """Log a summary of the census data.

    Provides detailed logging of bed availability across all campuses.

    Args:
        campus_data: Dictionary containing census data for all campuses with structure:
            {
                "campus_id": {
                    "general_beds": {"total": int, "available": int},
                    "icu_beds": {"total": int, "available": int},
                    "nicu_beds": {"total": int, "available": int},
                    "specialized_units": Dict[str, Any]
                }
            }
    """
    if not campus_data:
        logger.debug("No census data available to log")
        return

    logger.debug(
        "Successfully loaded census data for %d campuses",
        len(campus_data),
    )

    for campus_id, data in campus_data.items():
        general = data.get("general_beds", {"available": 0, "total": 0})
        icu = data.get("icu_beds", {"available": 0, "total": 0})
        nicu = data.get("nicu_beds", {"available": 0, "total": 0})

        logger.debug(
            "Campus %s - Beds: General=%d/%d, ICU=%d/%d, NICU=%d/%d",
            campus_id,
            general.get("available", 0),
            general.get("total", 0),
            icu.get("available", 0),
            icu.get("total", 0),
            nicu.get("available", 0),
            nicu.get("total", 0),
        )


def detect_specialization(unit_name: str, unit_id: str) -> Optional[str]:
    """Determine unit specialization from name and ID.

    Uses keyword matching to identify the medical specialization
    of a hospital unit based on its name or ID.

    Args:
        unit_name: Display name of the unit
        unit_id: Unique identifier for the unit

    Returns:
        str: Detected specialization (e.g., 'pediatric', 'cardiac'),
             or None if no match found
    """
    name_lower = unit_name.lower()
    id_lower = unit_id.lower()

    # Define specialization patterns
    specialization_patterns = {
        "pediatric": ["peds", "pediatric", "children", "child"],
        "cardiac": ["cardiac", "heart", "cvicu", "ccu"],
        "trauma": ["trauma", "emergency", "ed", "er"],
        "oncology": ["oncology", "cancer", "chemo"],
        "neurology": ["neuro", "stroke", "brain", "spine"],
        "burn": ["burn", "wound"],
        "transplant": ["transplant", "tx"],
    }

    # Check for matching patterns
    for spec, patterns in specialization_patterns.items():
        if any(pattern in name_lower or pattern in id_lower for pattern in patterns):
            return spec

    return None


def update_hospital_campuses(
    campus_file_path: str,
    census_info: Dict[str, Dict[str, Any]],
) -> bool:
    """Update hospital campuses with latest census information.

    Reads hospital data from JSON, updates bed counts and unit information
    from census data, and writes changes back to the file.

    Args:
        campus_file_path: Path to hospital campuses JSON file
        census_info: Dictionary mapping campus IDs to their census data

    Returns:
        bool: True if update was successful, False otherwise
    """
    file_path = Path(campus_file_path)
    if not file_path.exists():
        logger.error("Hospital campuses file not found: %s", file_path)
        return False

    try:
        # Read existing hospital data
        with file_path.open("r+", encoding="utf-8") as file:
            hospital_data = json.load(file)

        # Update each campus with census data
        for campus in hospital_data:
            campus_id = campus.get("campus_id")
            if not campus_id:
                continue

            # Get matching census data for this campus
            campus_census = census_info.get(campus_id)
            if not campus_census:
                logger.debug("No census data found for campus %s", campus_id)
                continue

            # Update bed counts
            campus["beds"] = {
                "general": {
                    "available": campus_census.get("general_beds", {}).get(
                        "available", 0
                    ),
                    "total": campus_census.get("general_beds", {}).get("total", 0),
                },
                "icu": {
                    "available": campus_census.get("icu_beds", {}).get("available", 0),
                    "total": campus_census.get("icu_beds", {}).get("total", 0),
                },
                "nicu": {
                    "available": campus_census.get(
                        "nicu_beds", {}).get("available", 0),
                    "total": campus_census.get("nicu_beds", {}).get("total", 0),
                },
            }

        # Write updated data back to the file
        with open(campus_file_path, "w", encoding="utf-8") as file:
            json.dump(hospital_data, file, indent=2)

        logger.info(
            "Successfully updated hospital campuses data with latest census information"
        )
        return True

    except (IOError, json.JSONDecodeError) as e:
        logger.error("Error processing census data: %s", str(e))
        return False


def update_census(
    census_file_path: Optional[str] = None,
    campus_file_path: Optional[str] = None,
) -> bool:
    """Update hospital campuses with current census data.

    Handles reading census data and updating hospital records with bed availability.

    Args:
        census_file_path: Path to census CSV file. Defaults to standard location.
        campus_file_path: Path to hospital campuses JSON. Defaults to standard location.

    Returns:
        bool: True if update succeeded, False otherwise.
    """
    # Configure file paths with defaults
    default_census = Path("data/census/current_census.csv")
    default_campuses = Path("data/hospitals/hospital_campuses.json")

    census_path = Path(census_file_path) if census_file_path else default_census
    campus_path = Path(campus_file_path) if campus_file_path else default_campuses

    # Read and validate census data
    census_info = read_census_data(str(census_path))
    if not census_info:
        logger.error("No census data available to process")
        return False

    # Update hospital records with census data
    update_success = update_hospital_campuses(
        str(campus_path),
        census_info
    )
    if not update_success:
        logger.error("Failed to update hospital records with census data")
        return False

    # Verify the update was applied
    try:
        with campus_path.open("r", encoding="utf-8") as file:
            updated_data = json.load(file)

        if not isinstance(updated_data, list):
            logger.error("Invalid hospital data format: expected list")
            return False

        # Check for successful updates
        updates_applied = any("bed_census" in campus for campus in updated_data)
        if not updates_applied:
            logger.warning("No campuses received census updates")
            return False

        logger.info("Successfully updated hospital census data")
        return True

    except (IOError, json.JSONDecodeError) as e:
        logger.error("Error verifying campus updates: %s", str(e), exc_info=True)
        return False


def print_census_summary(campus_id: str, census_dict: Dict[str, Any]) -> None:
    """Print a summary of the census data for a campus.

    Args:
        campus_id: ID of the campus to summarize
        census_dict: Dictionary containing census data for all campuses
    """
    if not campus_id or not census_dict:
        print("No census data available")
        return

    campus = census_dict.get(campus_id, {})
    if not campus:
        print(f"No census data found for campus {campus_id}")
        return

    try:
        # Get bed counts with safe defaults
        general = campus.get("general_beds", {"available": 0, "total": 0})
        icu = campus.get("icu_beds", {"available": 0, "total": 0})
        nicu = campus.get("nicu_beds", {"available": 0, "total": 0})

        # Generate output
        output = [
            f"\nCensus Summary for {campus_id}:",
            "-" * 50,
            f"General Beds: {general.get('available', 0)}/{general.get('total', 0)}",
            f"ICU Beds: {icu.get('available', 0)}/{icu.get('total', 0)}",
            f"NICU Beds: {nicu.get('available', 0)}/{nicu.get('total', 0)}",
        ]

        # Add specialized units if available
        if campus.get("specialized_units"):
            output.append("\nSpecialized Units:")
            for unit_name, unit_data in campus["specialized_units"].items():
                spec = unit_data.get("specialization", "Unspecified")
                avail = unit_data.get("available_beds", 0)
                total = unit_data.get("total_beds", 0)
                output.append(f"  - {unit_name} ({spec}): {avail}/{total}")

        print("\n".join(output))

    except (KeyError, AttributeError) as e:
        logger.error(
            "Error generating census summary for %s: %s",
            campus_id,
            str(e),
            exc_info=True,
        )
        print(f"Error generating census summary: {str(e)}")


if __name__ == "__main__":
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    # Update census data
    UPDATE_SUCCESS = update_census()
    if not UPDATE_SUCCESS:
        print("Failed to update census data")
        sys.exit(1)

    # Example usage:
    # Print census summary for a specific campus
    census_data = read_census_data("data/census/current_census.csv")
    if not census_data:
        print("No census data available")
        sys.exit(0)

    # Print summary for the first campus found
    first_campus = next(iter(census_data.keys()), None)
    if first_campus:
        print_census_summary(first_campus, census_data)
    else:
        print("No census data available")
