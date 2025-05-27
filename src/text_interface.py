import os
os.environ['PYTHONWARNINGS'] = 'ignore::FutureWarning' # Try to suppress warnings as early as possible

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning) # Fallback

import argparse
import json
import logging
import sys
import csv
import openai
import tiktoken
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim
from geopy.location import Location
from geopy.distance import geodesic
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
import rich # Added import
import rich.json # Added import
from .rag_components import get_exclusion_criteria_retriever # Added import
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn # Added Progress and columns

from .gui.hospital_search import HospitalSearch # type: ignore
from .core.models import HospitalCampus # type: ignore

from typing import Dict, Optional, Tuple, List, Any, Union # Ensure all are imported

# --- Constants ---
CONSOLE = Console(width=120)
# Geocoding setup
NOMINATIM_USER_AGENT = "tch_transfer_center_text_interface_v1"
# LLM Setup
OPENAI_API_KEY = "lm-studio"
OPENAI_API_BASE = "http://localhost:1234/v1"
LLM_MODEL_NAME = "deepseek-r1-medical-mini"

TARGET_HOSPITAL_KEYS = {
    "Texas Children's Hospital - Main Campus (MC)": {
        "campus_id": "TCH_MAIN_TMC", # Matches census/criteria keys
        "rag_yaml_key": "main_campus", # Key used in exclusion_criteria.yaml for RAG
        "display_name": "Texas Children's Hospital - Main Campus (MC)",
        "display_name_short": "TCH - Main",
        "address_for_geocoding": "6621 Fannin St, Houston, TX 77030"
    },
    "Texas Children's Hospital - The Woodlands": {
        "campus_id": "TCH_WOODLANDS",
        "rag_yaml_key": "the_woodlands_campus",
        "display_name": "Texas Children's Hospital - The Woodlands",
        "display_name_short": "TCH - Woodlands",
        "address_for_geocoding": "17600 I-45 South, The Woodlands, TX 77384"
    },
    "Texas Children's Hospital - West Campus (Katy)": {
        "campus_id": "TCH_WEST_KATY",
        "rag_yaml_key": "west_campus",
        "display_name": "Texas Children's Hospital - West Campus (Katy)",
        "display_name_short": "TCH - West",
        "address_for_geocoding": "18200 Katy Fwy, Houston, TX 77094"
    },
    "Texas Children's Pavilion for Women": {
        "campus_id": "TCH_PAVILION_WOMEN",
        "rag_yaml_key": "pavilion_for_women",
        "display_name": "Texas Children's Pavilion for Women",
        "display_name_short": "TCH - PFW",
        "address_for_geocoding": "6651 Main St, Houston, TX 77030" # Part of Main Campus complex
    },
    "Texas Children's Hospital North Austin Campus": { # Updated key to be more descriptive
        "campus_id": "TCH_NORTH_AUSTIN",
        "rag_yaml_key": "north_austin_campus",
        "display_name": "Texas Children's Hospital North Austin Campus",
        "display_name_short": "TCH - N. Austin",
        "address_for_geocoding": "9835 North Lake Creek Parkway, Austin, TX 78717"
    }
}

# Mapping from campus_id in data files to keys in TARGET_HOSPITAL_KEYS
# This allows linking LLM output (keyed by campus_id) back to our geocoded hospital list.
# This map might be redundant if campus_id in TARGET_HOSPITAL_KEYS values is always the definitive one.
CAMPUS_ID_TO_CRITERIA_KEY_MAP = {
    "TCH_MAIN_TMC": "Texas Children's Hospital - Main Campus (MC)",
    "TCH_WEST_KATY": "Texas Children's Hospital - West Campus (Katy)",
    "TCH_WOODLANDS": "Texas Children's Hospital - The Woodlands",
    "TCH_NORTH_AUSTIN": "Texas Children's Hospital North Austin Campus",
    "TCH_PAVILION_WOMEN": "Texas Children's Pavilion for Women"
}

# Hardcoded clinical vignette for testing
PATIENT_VIGNETTE_EXAMPLE = """
3-YEAR-OLD MALE PRESENTING WITH HIGH FEVER (39.5°C), INCREASED WORK OF BREATHING, AND DECREASED ORAL INTAKE FOR THE PAST 2 DAYS. HR 145, RR 35, BP 90/60, SPO2 93% ON RA. HISTORY OF PREMATURITY AT 32 WEEKS, PREVIOUS RSV BRONCHIOLITIS AT 6 MONTHS REQUIRING PICU ADMISSION AND BRIEF HFNC SUPPORT. CURRENTLY ON ALBUTEROL AND IPRATROPIUM NEBS WITH MINIMAL IMPROVEMENT.
"""

CENSUS_DATA_FILE_PATH = "/Users/derek/CascadeProjects/transfer_center/data/current_census.csv"

# --- Placeholder Clinical Criteria (USER SHOULD POPULATE THESE) ---
SPECIALTY_NEED_INDICATORS = """
- Significant respiratory distress (e.g., tachypnea, retractions, hypoxia not responsive to initial measures)
- Hemodynamic instability (e.g., persistent hypotension, poor perfusion despite fluid resuscitation)
- Acutely altered mental status or new focal neurological deficits
- Recurrent or prolonged seizures
- Suspected time-sensitive surgical emergency (e.g., acute abdomen, compartment syndrome)
- Severe trauma meeting regional trauma criteria
- Complex congenital conditions requiring immediate specialist intervention
- Need for advanced monitoring (e.g., invasive arterial line, intracranial pressure monitoring)
- Failure to respond to appropriate initial treatments at the sending facility
"""

# --- Logger Setup ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Ensure the logger processes DEBUG messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') # Console logging

# Configure logging for external libraries to reduce verbosity
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
logging.getLogger("faiss").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING) # Reduce HTTP request logging

# File logger setup for DEBUG level
log_file_path = os.path.join(os.path.dirname(__file__), "transfer_center_debug.log")
file_handler = logging.FileHandler(log_file_path, mode='w') # 'w' to overwrite log each run, 'a' to append
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)
logger.propagate = False  # Prevent messages from reaching the root logger's console handler

# Also ensure root logger also gets the file handler if not using a specific logger instance everywhere
# logging.getLogger().addHandler(file_handler) # If using root logger directly

logger.info("Application started. Logging to console (INFO and above) and to file (DEBUG and above).")
logger.debug(f"Full log file path: {log_file_path}")

# --- Tokenizer Setup (tiktoken) ---
try:
    # Using a common encoding that works well for many models, including Llama.
    # For Llama 3, 'cl100k_base' is a good general choice if specific tokenizer isn't published.
    # If LM Studio uses a very specific tokenizer for Llama-3 that tiktoken doesn't perfectly match,
    # this will still provide a very close estimate.
    encoding = tiktoken.get_encoding("cl100k_base") 
except Exception as e:
    logger.warning(f"Could not load tiktoken encoding 'cl100k_base', falling back to 'p50k_base'. Error: {e}")
    try:
        encoding = tiktoken.get_encoding("p50k_base") # A more general fallback
    except Exception as e_fallback:
        logger.error(f"Could not load any tiktoken encoding. Token counting will be disabled. Error: {e_fallback}")
        encoding = None

if encoding:
    logger.info(f"Tiktoken encoding '{encoding.name}' loaded successfully for token counting.")
else:
    logger.warning("Tiktoken encoding not available. Prompt token counts will not be logged.")

# --- Helper Functions for LLM Interaction ---
def count_tokens(text: str) -> int:
    """Estimates the number of tokens in a string using tiktoken."""
    if not encoding:
        return -1 # Indicates token counting is disabled
    return len(encoding.encode(text))

def execute_llm_chat_completion(client: openai.OpenAI, system_message: str, user_prompt: str, step_name: str, temperature=0.7, specific_json_schema: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Executes a chat completion call to the LLM and handles potential errors, including token count logging."""
    logger.debug(f"Executing LLM chat completion for: {step_name}")
    
    system_tokens = count_tokens(system_message)
    user_tokens = count_tokens(user_prompt)
    total_prompt_tokens = system_tokens + user_tokens

    if encoding: # Only log if encoding is available
        logger.debug(f"[{step_name}] System prompt token count: ~{system_tokens}")
        logger.debug(f"[{step_name}] User prompt token count: ~{user_tokens}")
        logger.debug(f"[{step_name}] Total estimated prompt tokens: ~{total_prompt_tokens}")
        # Add a warning if approaching a typical context limit, e.g., 8k or a user-defined one
        # For now, just logging. We can add warnings later if needed based on your LM Studio settings.

    max_retries = 3
    retry_delay = 5  # seconds

    CONSOLE.print(f"Querying LLM for {step_name}...", style="bold yellow")
    # Log the full prompts to the debug file for detailed inspection
    logger.debug(f"[{step_name}] System Prompt:\n{system_message}")
    logger.debug(f"[{step_name}] User Prompt:\n{user_prompt}")

    try:
        # Determine the schema to use
        schema_name = f"{step_name.lower().replace(' ', '_').replace('.', '')}_schema"
        current_schema_definition = specific_json_schema if specific_json_schema else {
            "type": "object",
            "additionalProperties": True
        }

        api_response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": "true",
                "schema": current_schema_definition
            }
        }
        # Log the schema being used for this step for easier debugging
        logger.debug(f"[{step_name}] Using JSON schema for response_format: {json.dumps(api_response_format, indent=2)}")

        completion = client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            response_format=api_response_format
        )
        response_content = completion.choices[0].message.content

        # Attempt to parse the JSON response
        # The LLM should ideally return only JSON when response_format is set,
        # but we'll keep the robust parsing just in case.
        json_start_index = response_content.find('{')
        json_end_index = response_content.rfind('}')

        if json_start_index != -1 and json_end_index != -1 and json_start_index < json_end_index:
            json_string = response_content[json_start_index : json_end_index + 1]
            try:
                parsed_json = json.loads(json_string)
                # Optionally, print the clean JSON that was successfully parsed
                # CONSOLE.print(f"Successfully parsed LLM JSON response:\n{json.dumps(parsed_json, indent=2)}")
                return parsed_json
            except json.JSONDecodeError as e:
                CONSOLE.print(f"[bold red]Failed to parse LLM JSON response: {e}[/bold red]")
                CONSOLE.print(f"Raw LLM response snippet for debugging:\n{response_content[:500]}...") # Print more for context
                return None
        else:
            CONSOLE.print("[bold red]Could not find valid JSON structure in LLM response.[/bold red]")
            CONSOLE.print(f"Raw LLM response for debugging:\n{response_content}")
            return None

    except openai.APIConnectionError as e:
        CONSOLE.print(f"[bold red]Error during LLM API call: {e}[/bold red]")
        return None

# Define the specific JSON schema for Step 2 Specialty Needs
STEP_2_SPECIALTY_NEEDS_SCHEMA = {
    "type": "object",
    "properties": {
        "specialties_assessment": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "specialty_name": {"type": "string"},
                    "likelihood_score": {"type": "integer", "minimum": 0, "maximum": 100},
                    "reasoning_from_vignette": {"type": "string"}
                },
                "required": ["specialty_name", "likelihood_score", "reasoning_from_vignette"]
            },
            "minItems": 1 # Expect at least one specialty assessment based on prompt example
        },
        "llm_reasoning_notes": {"type": "string"}
    },
    "required": ["specialties_assessment", "llm_reasoning_notes"]
}

# --- Location and Distance Calculation Functions ---
def get_location(hospital_name: str, geolocator: Nominatim, hospital_cache: Dict[str, Dict[str, Any]]) -> Optional[Location]:
    # Check cache first
    cached_entry = hospital_cache.get(hospital_name)
    if cached_entry and isinstance(cached_entry, dict):
        lat = cached_entry.get('latitude')
        lon = cached_entry.get('longitude')
        # Ensure address is a string, use hospital_name as fallback if address is not in cache or is None
        address_from_cache = cached_entry.get('address')
        display_address = address_from_cache if isinstance(address_from_cache, str) else hospital_name

        if lat is not None and lon is not None:
            CONSOLE.print(f"Found '{hospital_name}' in cache.")
            # Construct a geopy.location.Location object
            # The 'point' argument expects (latitude, longitude, [altitude])
            return Location(address=display_address, point=(lat, lon), raw=cached_entry)
    
    # If not in cache or cache format is different, geocode
    CONSOLE.print(f"'{hospital_name}' not in cache or cache data incomplete, attempting geocoding...")
    try:
        # Use a slightly longer timeout for geocoding attempts
        location_data = geolocator.geocode(hospital_name, timeout=15) # Increased timeout
        if location_data:
            CONSOLE.print(f"Successfully geocoded '{hospital_name}'.")
            return location_data
        else:
            CONSOLE.print(f"Geocoding failed for '{hospital_name}'. No location found by geocoder.")
            return None
    except GeocoderTimedOut:
        CONSOLE.print(f"Geocoding timed out for '{hospital_name}'.")
        return None
    except GeocoderUnavailable as e:
        CONSOLE.print(f"Geocoder unavailable for '{hospital_name}': {e}")
        return None
    except Exception as e:
        CONSOLE.print(f"An unexpected error occurred during geocoding for '{hospital_name}': {e}")
        return None

def calculate_distance(loc1: Location, loc2: Location) -> Optional[float]:
    """Calculates geodesic distance in miles between two Location objects."""
    if loc1 and loc2:
        distance_km = geodesic((loc1.latitude, loc1.longitude), (loc2.latitude, loc2.longitude)).km
        distance_miles = distance_km * 0.621371
        return distance_miles
    return None

def get_user_input_for_vignette() -> str:
    return PATIENT_VIGNETTE_EXAMPLE

def load_census_data(file_path: str) -> dict:
    """Loads census data from a CSV file and organizes it by campus_id."""
    census_by_campus = {}
    file_opened_successfully = False
    logger.debug(f"Attempting to load census data from: {file_path}")
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            file_opened_successfully = True
            logger.debug(f"File {file_path} opened successfully.")
            
            # Filter out empty lines before passing to DictReader
            # This handles cases where there might be leading blank lines
            non_empty_lines = (line for line in f if line.strip())
            
            reader = csv.DictReader(non_empty_lines)
            
            if not reader.fieldnames: # Check if headers are missing (empty file or malformed after filtering)
                CONSOLE.print(f"[bold red]Error: Census CSV file [cyan]{file_path}[/cyan] is effectively empty or has no headers after skipping blank lines.[/bold red]")
                logger.error(f"Census CSV file {file_path} is effectively empty or has no headers after skipping blank lines. Fieldnames: {reader.fieldnames}")
                return {}
            logger.debug(f"CSV headers identified: {reader.fieldnames}")

            for i, row in enumerate(reader):
                logger.debug(f"Processing CSV row {i+1}: {row}")
                campus_id = row.get("campus_id")
                if campus_id and campus_id.strip(): # Ensure campus_id is not None or empty/whitespace
                    campus_id = campus_id.strip()
                    logger.debug(f"Row {i+1}: Found campus_id '{campus_id}'.")
                    if campus_id not in census_by_campus:
                        census_by_campus[campus_id] = []
                    census_by_campus[campus_id].append(row)
            
            logger.debug(f"Finished processing CSV. Total rows read: {i+1}. Resulting dict keys: {list(census_by_campus.keys())}")

        if census_by_campus: # Data was successfully organized
            CONSOLE.print(f"Successfully loaded and processed census data from [cyan]{file_path}[/cyan]. Organized data for {len(census_by_campus)} campuses.")
            logger.info(f"Successfully loaded census data for {len(census_by_campus)} campuses from {file_path}.")
        elif file_opened_successfully: # File was opened and parsed, but resulted in an empty dictionary
            CONSOLE.print(f"[yellow]Warning: Census data file [cyan]{file_path}[/cyan] was loaded, but it's an empty JSON object or contains no data.[/yellow]")
            logger.warning(f"Census data file {file_path} is empty or contains no data after parsing.")
        return census_by_campus
    except FileNotFoundError:
        CONSOLE.print(f"[bold red]Error: Census data file not found at {file_path}[/bold red]")
        logger.error(f"Census data file not found at {file_path}", exc_info=True)
        return {}
    except Exception as e:
        CONSOLE.print(f"[bold red]An error occurred while loading/processing census data from {file_path}: {e}[/bold red]")
        logger.error(f"Unexpected error loading census data from {file_path}: {e}", exc_info=True)
        return {}

# --- Geocoding and Distance Calculation ---
def get_geolocator() -> Nominatim:
    """Initializes and returns a Nominatim geolocator."""
    return Nominatim(user_agent=NOMINATIM_USER_AGENT)

def get_distance(loc1: Location, loc2: Location) -> float:
    """Calculates geodesic distance in miles between two geopy Locations."""
    distance_km = geodesic((loc1.latitude, loc1.longitude), (loc2.latitude, loc2.longitude)).km
    distance_miles = distance_km * 0.621371
    return distance_miles

# --- Main Application Logic ---
def display_consolidated_assessment_summary(
    consolidated_assessment: Dict[str, Any],
    hospital_keys_map: Dict[str, Dict[str, Any]],
    patient_vignette: str,
    extracted_entities: Dict[str, Any],
    specialty_needs: Dict[str, Any]
):
    """Displays the consolidated hospital assessments in a formatted way using Rich."""
    CONSOLE.print(Panel("Consolidated Hospital Assessment Summary", style="bold magenta", expand=False))

    if not consolidated_assessment or not isinstance(consolidated_assessment, dict):
        CONSOLE.print("[yellow]No consolidated assessment data to display or data is not in expected format.[/yellow]")
        return

    # Create a mapping from campus_id to full display name for easier lookup
    # hospital_keys_map has full name as key and dict of details (including campus_id) as value
    # We want: { campus_id_value: full_name_key }
    id_to_display_name = {details['campus_id']: name for name, details in hospital_keys_map.items()}

    # Display Patient Vignette and Extracted Entities first
    display_patient_and_extracted_info(patient_vignette, extracted_entities, specialty_needs)

    for campus_id, assessment in consolidated_assessment.items():
        display_name = id_to_display_name.get(campus_id, campus_id) # Fallback to campus_id if not in map
        
        if not isinstance(assessment, dict):
            CONSOLE.print(Panel(f"[bold red]Error: Assessment data for {display_name} is not a dictionary.[/bold red]", title=f"{display_name}", border_style="red"))
            continue

        content = Text()
        
        decision = assessment.get("overall_transfer_decision", "N/A")
        decision_icon = ""
        decision_style = ""
        if "Suitable" in decision:
            decision_icon = "✅ "
            decision_style = "green"
        elif "Unsuitable" in decision:
            decision_icon = "❌ "
            decision_style = "red"
        elif "Needs More Info" in decision:
            decision_icon = "❓ "
            decision_style = "yellow"
        else:
            decision_icon = "⚠️ " 
            decision_style = "orange3"

        content.append(f"{decision_icon}Overall Decision: ", style=f"bold {decision_style}")
        content.append(f"{decision}\n", style=decision_style)

        primary_reasons = assessment.get("primary_exclusion_reasons", [])
        if isinstance(primary_reasons, list) and primary_reasons:
            content.append("Primary Exclusion Reasons:\n", style="bold")
            for reason in primary_reasons:
                content.append(f"  - {reason}\n")
        elif isinstance(primary_reasons, str):
             content.append("Primary Exclusion Reasons:\n  - ", style="bold")
             content.append(f"{primary_reasons}\n")
        else:
            content.append("Primary Exclusion Reasons: ", style="bold")
            content.append("None explicitly listed or N/A\n")

        content.append("\nAdjudicated Criteria:\n", style="bold")
        has_criteria = False
        for crit_type in ["general_criteria_adjudication", "departmental_criteria_adjudication"]:
            criteria_list = assessment.get(crit_type, [])
            if criteria_list:
                has_criteria = True
                content.append(f"{crit_type.replace('_', ' ').title()}:\n", style="italic")
                for criterion in criteria_list:
                    if isinstance(criterion, dict):
                        stmt = criterion.get("criterion_statement", "N/A")
                        is_met_exclusion = criterion.get("is_met_for_exclusion", False)
                        icon = "❌" if is_met_exclusion else "✅"
                        reasoning = criterion.get("reasoning_from_vignette", "")
                        content.append(f"  {icon} {stmt} (Excludes: {is_met_exclusion})\n")
                        if reasoning:
                            content.append(f"      Reasoning: {reasoning}\n", style="dim")
                    else:
                        content.append(f"  - Malformed criterion entry.\n") # Should not happen with Pydantic
        if not has_criteria:
            content.append("  No specific criteria adjudicated or RAG snippets provided to LLM.\n")

        census_summary = assessment.get("census_impact_summary", {})
        if isinstance(census_summary, dict):
            content.append("\nCensus Impact:\n", style="bold")
            unit = census_summary.get("relevant_unit_type", "N/A")
            beds = census_summary.get("available_beds", "N/A")
            notes = census_summary.get("notes", "N/A")
            beds_icon = "✅" if "Sufficient" in str(beds) or (isinstance(beds, (int, float)) and beds > 0) else "⚠️"
            if "capacity" in str(notes).lower() or "full" in str(notes).lower() or (isinstance(beds, (int, float)) and beds == 0):
                beds_icon = "❌"
            content.append(f"  Unit: {unit}\n")
            content.append(f"  {beds_icon} Available Beds: {beds}\n")
            content.append(f"  Notes: {notes}\n")
        else:
            content.append("\nCensus Impact: ", style="bold")
            content.append("Data malformed or N/A\n")

        llm_notes = assessment.get("llm_reasoning_notes", "N/A")
        content.append("\nLLM Reasoning Notes:\n", style="bold")
        content.append(f"  {llm_notes}\n")

        CONSOLE.print(Panel(content, title=f"[bold cyan]{display_name}[/bold cyan]", border_style="cyan", expand=True))


def display_patient_and_extracted_info(patient_vignette: str, extracted_entities: Dict[str, Any], specialty_needs: Dict[str, Any]):
    """Displays the patient vignette and extracted entities in a formatted way."""
    CONSOLE.print(Panel(Text(patient_vignette, justify="left"), title="[bold magenta]Patient Vignette Being Used[/bold magenta]", border_style="magenta", expand=False))
    CONSOLE.print(Panel("Sending Facility: Houston Methodist Hospital (Hardcoded for this session)", title="[bold blue]Context[/bold blue]", border_style="blue", expand=False))

    if extracted_entities:
        CONSOLE.print(Panel("Extracted Clinical Information:", title="[bold green]Step 1: Extracted Entities[/bold green]", border_style="green", expand=False))
        for key, value in extracted_entities.items():
            CONSOLE.print(f"[bold blue]{key}[/bold blue]: {value}")
    else:
        CONSOLE.print(Panel("[bold red]No extracted entities available.[/bold red]", title="[bold green]Step 1: Extracted Entities[/bold green]", border_style="green", expand=False))

    if specialty_needs:
        CONSOLE.print(Panel("Identified Specialty Needs:", title="[bold green]Step 2: Specialty Needs[/bold green]", border_style="green", expand=False))
        for key, value in specialty_needs.items():
            CONSOLE.print(f"[bold blue]{key}[/bold blue]: {value}")
    else:
        CONSOLE.print(Panel("[bold red]No specialty needs identified.[/bold red]", title="[bold green]Step 2: Specialty Needs[/bold green]", border_style="green", expand=False))


def main():
    """Main function to run the text-based interface."""
    # Initialize OpenAI client for LM Studio
    client = openai.OpenAI(base_url=OPENAI_API_BASE, api_key=OPENAI_API_KEY)
    logger.info(f"OpenAI client initialized. Using model: {LLM_MODEL_NAME} via {OPENAI_API_BASE}")

    parser = argparse.ArgumentParser(description="Transfer Center Text Interface")
    parser.add_argument(
        "--patient_description",
        type=str,
        help="Clinical vignette/patient description to use for the evaluation.",
        default=None # Default to None, so we can check if it was provided
    )
    parser.add_argument(
        "--primary_service",
        type=str,
        help="Primary service requested for the patient (e.g., Neurology, Cardiology).",
        default=None
    )
    parser.add_argument(
        "--current_location",
        type=str,
        help="Current location of the patient or sending facility.",
        default=None
    )
    parser.add_argument(
        "--verbose",
        action="store_true", # Makes it a boolean flag
        help="Enable verbose output, including debug messages and detailed RAG snippets.",
        default=False
    )
    args = parser.parse_args()

    # Determine which patient vignette to use
    if args.patient_description:
        current_patient_vignette = args.patient_description
        if args.verbose:
            logger.info("Using patient description provided via command-line argument.")
    else:
        current_patient_vignette = PATIENT_VIGNETTE_EXAMPLE
        if args.verbose:
            logger.info("No patient description provided via command-line, using default example vignette.")

    # Initialize RAG retriever for exclusion criteria
    if args.verbose:
        CONSOLE.print("Initializing Exclusion Criteria RAG retriever...", style="bold blue")
    exclusion_criteria_retriever = get_exclusion_criteria_retriever()
    if exclusion_criteria_retriever:
        if args.verbose:
            CONSOLE.print("[green]Exclusion Criteria RAG retriever initialized successfully.[/green]")
    else:
        CONSOLE.print("[bold red]Failed to initialize Exclusion Criteria RAG retriever. Step 3 may not have RAG context.[/bold red]")

    # Initialize HospitalSearch and load data
    hospital_search = HospitalSearch()
    # Load census data
    census_data = load_census_data(CENSUS_DATA_FILE_PATH)

    # --- Display Initial Context ---
    CONSOLE.print(Panel(Text(current_patient_vignette, justify="left"), title="[bold magenta]Patient Vignette Being Used[/bold magenta]", border_style="magenta", expand=False))
    # Display primary service and current location if provided
    if args.primary_service:
        CONSOLE.print(Panel(f"Primary Service Requested: {args.primary_service}", title="[bold blue]Context[/bold blue]", border_style="blue", expand=False))
    if args.current_location:
        CONSOLE.print(Panel(f"Sending Facility/Location: {args.current_location}", title="[bold blue]Context[/bold blue]", border_style="blue", expand=False))
    else:
        CONSOLE.print(Panel("Sending Facility: Houston Methodist Hospital (Hardcoded for this session)", title="[bold blue]Context[/bold blue]", border_style="blue", expand=False))

    if census_data:
        if args.verbose:
            CONSOLE.print(f"[dim]Successfully loaded and processed census data from {CENSUS_DATA_FILE_PATH}.[/dim]")
            CONSOLE.print(f"[dim]Organized data for {len(census_data)} campuses.[/dim]")
    else:
        CONSOLE.print("[bold red]Failed to load census data. This may impact evaluations.[/bold red]")
    
    CONSOLE.line() # Add a blank line for spacing before progress bar

    # Overall script progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=CONSOLE,
        transient=False # Keep progress visible after completion
    ) as overall_progress:
        main_task = overall_progress.add_task("Overall Progress", total=4) # Generic description

        # Step 1: Extract Clinical Information
        # No longer update main_task description here, Panel handles it.
        if args.verbose:
            CONSOLE.print(Panel("Step 1: Extract Clinical Information", style="bold blue"))
        USER_PROMPT_STEP1_TEMPLATE = """# Clinical Vignette Analysis - Step 1: Extract Clinical Information

You are an expert clinical information extractor. Respond ONLY with a valid JSON object. Do not include any text before or after the JSON.

Context:
The sending facility is Houston Methodist Hospital (location unknown).

Vignette:
{patient_vignette}

Task:
From the vignette, extract all relevant clinical information explicitly mentioned. Present this as a structured JSON object.
Ensure all string values are properly quoted. For boolean concepts, use true or false. For numerical values, use numbers.
Within the 'patient_details' object, include a 'patient_description' field which is a concise, one-sentence summary of the patient (e.g., '3-year-old male with a history of prematurity and previous RSV bronchiolitis requiring PICU admission.').
Use the 'llm_reasoning_notes' field for any ambiguities, information that doesn't fit other fields, or general observations about the vignette's content or clarity.

Example JSON Structure (adapt as needed based on the vignette's content):
{{{{ # Note: Using double curlies to escape for f-string, then single for JSON
    "patient_details": {{
        "patient_description": "3-year-old male with history of prematurity at 32 weeks and previous RSV bronchiolitis at 6 months requiring PICU admission and HFNC support.",
        "age_years": 3, 
        "gender": "male", 
        "history_prematurity_weeks": 32, 
        "history_rsv_picu_hfnc": true 
    }},
    "presenting_complaint": {{
        "symptoms": ["high fever", "increased work of breathing", "decreased oral intake"], 
        "duration_days": 2 
    }},
    "vital_signs": {{
        "temperature_celsius": 39.5, 
        "heart_rate": 145, 
        "respiratory_rate": 35, 
        "bp_systolic": 90, 
        "bp_diastolic": 60, 
        "spo2_room_air_percent": 93 
    }},
    "current_treatment_and_response": {{
        "medications": ["albuterol nebs", "ipratropium nebs"], 
        "response": "minimal improvement" 
    }},
    "llm_reasoning_notes": "Vignette is concise. 'Minimal improvement' to nebs is noted. Prematurity and RSV history are significant. No allergies mentioned."
}}}}

Your Output (JSON only):
"""

        user_prompt_step1 = USER_PROMPT_STEP1_TEMPLATE.format(patient_vignette=current_patient_vignette)
        extracted_entities = execute_llm_chat_completion(
            client,
            "You are an expert clinical information extractor. Respond ONLY with a valid JSON object. Do not include any text before or after the JSON.",
            user_prompt_step1,
            step_name="Step 1 Extraction"
        )
        if extracted_entities:
            if args.verbose:
                logger.info(f"Successfully extracted entities: {json.dumps(extracted_entities)}")
                CONSOLE.print("[green]Step 1: Clinical Information Extracted Successfully.[/green]")
                # Pretty print the JSON response from the LLM for step 1
                CONSOLE.print(Panel(rich.json.JSON(json.dumps(extracted_entities)), title="[bold green]Extracted Clinical Entities (JSON)[/bold green]", border_style="green", expand=False))
        else:
            CONSOLE.print("[bold red]Step 1: Failed to extract clinical information. Cannot proceed.[/bold red]")
            # Early exit or handle error appropriately if Step 1 fails
            return
        overall_progress.advance(main_task)

        # Step 2: Identify Specialty Needs
        # No longer update main_task description here, Panel handles it.
        if args.verbose:
            CONSOLE.print(Panel("Step 2: Identify Specialty Needs", style="bold blue"))
        if extracted_entities:
            USER_PROMPT_STEP2_TEMPLATE = """# Clinical Vignette Analysis - Step 2: Identify Specialty Needs

You are an expert triage physician. Your task is to assess potential medical specialty needs based on clinical information and provided indicators. Respond ONLY with a valid JSON object.

Extracted Clinical Entities:
{clinical_info}

Provided Specialty Need Indicators (for guidance, not exhaustive):
{specialty_need_indicators}

Task:
Based on the 'Extracted Clinical Entities' and the 'Specialty Indicators', identify potential medical specialties the patient might need. For each identified specialty, provide a 'likelihood_score' (0-100) and brief 'reasoning_from_vignette'.
Output a structured JSON object. Adapt the example structure if needed.

Example JSON Structure (adapt as needed):
{{{{ # Note: Using double curlies to escape for f-string, then single for JSON
    "specialties_assessment": [
        {{
            "specialty_name": "Pediatric Critical Care (PICU)",
            "likelihood_score": 90,
            "reasoning_from_vignette": "Patient exhibits significant respiratory distress (SpO2 93% RA, increased WOB) and minimal improvement to initial nebs, aligning with indicators for advanced monitoring and respiratory support."
        }},
        {{
            "specialty_name": "Pediatric Emergency Medicine",
            "likelihood_score": 100,
            "reasoning_from_vignette": "Acute presentation with high fever and respiratory distress warrants immediate evaluation by pediatric emergency specialists."
        }}
    ],
    "llm_reasoning_notes": "The need for PICU is high given the history and current presentation. If not PICU, at least a high-acuity pediatric inpatient unit with strong respiratory support capabilities is essential. The indicators provided were helpful in confirming these needs."
}}}}

Your Output (JSON only):
"""

            user_prompt_step2 = USER_PROMPT_STEP2_TEMPLATE.format(
                clinical_info=json.dumps(extracted_entities, indent=2),
                specialty_need_indicators=SPECIALTY_NEED_INDICATORS
            )
            specialty_needs = execute_llm_chat_completion(
                client,
                "You are an expert triage physician. Your task is to assess potential medical specialty needs based on clinical information and provided indicators. Respond ONLY with a valid JSON object.",
                user_prompt_step2,
                step_name="Step 2 Specialty Needs",
                specific_json_schema=STEP_2_SPECIALTY_NEEDS_SCHEMA
            )
            if specialty_needs:
                if args.verbose:
                    logger.info(f"Successfully identified specialty needs: {json.dumps(specialty_needs)}")
                    CONSOLE.print("[green]Step 2: Specialty Needs Determined Successfully.[/green]")
                    CONSOLE.print(Panel(rich.json.JSON(json.dumps(specialty_needs)), title="[bold green]Determined Specialty Needs (JSON)[/bold green]", border_style="green", expand=False))
            else:
                CONSOLE.print("[bold red]Step 2: Failed to determine specialty needs. This may impact hospital evaluation.[/bold red]")
                # Decide if to proceed without specialty_needs or return
        else:
            logger.error("Skipping Step 2 because Step 1 failed.")
            CONSOLE.print(Panel("[bold yellow]Step 2: Skipped due to Step 1 failure[/bold yellow]", border_style="yellow"))
        overall_progress.advance(main_task)

        # Step 3: Evaluate Hospitals for Exclusion Criteria & Bed Availability
        # No longer update main_task description here, Panel handles it.
        if args.verbose:
            CONSOLE.print(Panel("Step 3: Evaluate Hospitals for Exclusion Criteria & Bed Availability", style="bold blue"))
        hospital_eval_total = len(TARGET_HOSPITAL_KEYS)
        hospital_eval_task_id = overall_progress.add_task(
            description=f"[plum4]Pending Hospital Evaluations (0/{hospital_eval_total})", 
            total=hospital_eval_total
        )

        all_individual_assessments = {}
        all_individual_assessment_objects_for_consolidation = []

        for i, (hospital_dict_key, target_campus_details) in enumerate(TARGET_HOSPITAL_KEYS.items()):
            # Update description for the hospital evaluation sub-task
            overall_progress.update(
                hospital_eval_task_id, 
                description=f"[plum4]Evaluating ({i+1}/{hospital_eval_total}): {target_campus_details['display_name_short']}"
            )

            # Get the key used for RAG filtering from the details
            current_rag_yaml_key = target_campus_details['rag_yaml_key']

            # Hardcoded exclusion for PAVILION_FOR_WOMEN
            if current_rag_yaml_key == "pavilion_for_women": # Use the RAG key for this check too
                specific_exclusion_criteria_json = json.dumps([
                    {
                        "criterion_id": "PFW_PREG_FEMALE_ONLY",
                        "criterion_type": "absolute_exclusion",
                        "department_name": "N/A",
                        "criterion_statement": "Patient must be a pregnant female. All other patient types are automatically excluded from PAVILION_FOR_WOMEN.",
                        "applies_to_age_min": None, # Python None becomes JSON null via json.dumps
                        "applies_to_age_max": None,
                        "keywords": ["pregnant", "female", "obstetrics", "women's health", "maternity"]
                    }
                ], indent=2)
                individual_assessment = {
                    "overall_transfer_decision": "Unsuitable",
                    "primary_exclusion_reasons": ["Patient is not a pregnant female."],
                    "llm_reasoning_notes": f"Patient does not meet the primary specialty criteria for PAVILION_FOR_WOMEN."
                }
                all_individual_assessments[target_campus_details['campus_id']] = individual_assessment
                assessment_wrapper_for_consolidation = {"campus_id": target_campus_details['campus_id'], "evaluation": individual_assessment}
                all_individual_assessment_objects_for_consolidation.append(assessment_wrapper_for_consolidation)
                if args.verbose:
                    CONSOLE.print(f"[green]Individual assessment for {target_campus_details['campus_id']} completed (hardcoded exclusion).[/green]")
            else:
                criteria_campus_key = CAMPUS_ID_TO_CRITERIA_KEY_MAP.get(target_campus_details['campus_id'], target_campus_details['campus_id'])
                
                specific_exclusion_criteria_json = "" # Assuming this is usually empty and RAG is primary
                specific_census_data_json = json.dumps(census_data.get(target_campus_details['campus_id'], {}), indent=2)

                # RAG Integration: Retrieve relevant criteria snippets
                retrieved_criteria_snippets_str = "No specific criteria snippets retrieved."
                if exclusion_criteria_retriever and extracted_entities and specialty_needs:
                    query_parts = []
                    if isinstance(extracted_entities, dict):
                        patient_description = extracted_entities.get("patient_details", {}).get("patient_description", "")
                        presenting_complaint_symptoms = extracted_entities.get("presenting_complaint", {}).get("symptoms", [])
                        if patient_description: query_parts.append(patient_description)
                        if presenting_complaint_symptoms: query_parts.append("Symptoms: " + ", ".join(presenting_complaint_symptoms))
                    
                    if isinstance(specialty_needs, dict):
                        specialties_assessment_list = specialty_needs.get("specialties_assessment", [])
                        if isinstance(specialties_assessment_list, list):
                            for assessment_item in specialties_assessment_list:
                                if isinstance(assessment_item, dict):
                                    specialty_name = assessment_item.get("specialty_name", "")
                                    reasoning = assessment_item.get("reasoning_from_vignette", "")
                                    if specialty_name: query_parts.append(f"Requires specialty: {specialty_name}")
                                    if reasoning: query_parts.append(reasoning)
                            llm_reasoning = specialty_needs.get("llm_reasoning_notes", "")
                            if llm_reasoning: query_parts.append(llm_reasoning)

                    rag_query = " ".join(query_parts).strip()

                    if rag_query:
                        if args.verbose:
                            logger.info(f"RAG Query for {target_campus_details['campus_id']}: {rag_query}")
                        try:
                            # --- MODIFICATION START: Configure retriever for current hospital ---
                            current_retriever_for_invoke = exclusion_criteria_retriever # Default to the general one
                            # REMOVED: Retriever-level filtering as it seems ineffective.
                            # Python-based filtering will be used after the invoke call.
                            # if exclusion_criteria_retriever and hasattr(exclusion_criteria_retriever, 'vectorstore') and target_campus_details['campus_id']:
                            #     logger.info(f"Configuring RAG retriever specifically for hospital_id: {target_campus_details['campus_id']}")
                            #     current_retriever_for_invoke = exclusion_criteria_retriever.vectorstore.as_retriever(
                            #         search_kwargs={'filter': {'hospital_id': target_campus_details['campus_id']}}
                            #     )
                            # elif not target_campus_details['campus_id']:
                            #     logger.warning(f"target_campus_id is None or empty for {target_campus_details['display_name_short']}. Using general RAG retriever for invoke call.")
                            # --- MODIFICATION END ---
                            
                            # Use the general retriever for the invoke call
                            all_retrieved_docs = current_retriever_for_invoke.invoke(rag_query)
                            
                            # DEBUG: Print info about all_retrieved_docs immediately after invoke
                            if args.verbose: 
                                CONSOLE.print(f"DEBUG (post-invoke): For {target_campus_details['campus_id']}, all_retrieved_docs count: {len(all_retrieved_docs) if all_retrieved_docs else 0}", style="bold magenta")
                                if all_retrieved_docs:
                                    for i, doc_debug in enumerate(all_retrieved_docs[:5]): # Print metadata of first 5 raw retrieved docs
                                        CONSOLE.print(f"  DEBUG (post-invoke) Doc {i+1} metadata: {doc_debug.metadata}", style="magenta")
                            
                            hospital_filtered_docs_for_prompt = [] # Docs that will actually be used in the prompt
                            if all_retrieved_docs:
                                # This loop now iterates over docs already (ideally) filtered by the retriever,
                                # or acts as the primary filter if retriever-level filtering didn't happen.
                                # It also handles cases where a doc might have no hospital_id (general criteria).
                                for doc in all_retrieved_docs:
                                    doc_meta_hospital_id = doc.metadata.get("hospital_id")
                                    # Include if doc is specific to current hospital OR if doc is general (no hospital_id)
                                    if doc_meta_hospital_id == current_rag_yaml_key or not doc_meta_hospital_id:
                                        hospital_filtered_docs_for_prompt.append(doc)
                            
                            if hospital_filtered_docs_for_prompt:
                                if args.verbose:
                                    CONSOLE.print(f"DEBUG (prompt prep): Count of hospital_filtered_docs_for_prompt for {current_rag_yaml_key}: {len(hospital_filtered_docs_for_prompt)}")
                                temp_snippets = []
                                if args.verbose:
                                    CONSOLE.print(f"--- Filtered RAG Snippets for Prompt: {target_campus_details['display_name_short']} (RAG Key: {current_rag_yaml_key}) ---", style="yellow")
                                for i, doc in enumerate(hospital_filtered_docs_for_prompt[:3]): # Use top 3 of filtered docs
                                    if args.verbose:
                                        CONSOLE.print(f"DEBUG (prompt prep): Doc metadata for {current_rag_yaml_key}, Snippet {i+1}: {doc.metadata}")
                                    source = doc.metadata.get('source_file', 'N/A')
                                    category = doc.metadata.get('criterion_category', 'N/A')
                                    snippet_text = f"  Snippet {i+1} (Source: {source}, Category: {category}):\n    - {doc.page_content}"
                                    temp_snippets.append(snippet_text)
                                    CONSOLE.print(Text(snippet_text, style="grey70"))
                                retrieved_criteria_snippets_str = "\n".join(temp_snippets)
                                if args.verbose:
                                    CONSOLE.print(f"--- End Filtered RAG Snippets for Prompt: {target_campus_details['display_name_short']} ---", style="yellow")
                                    # Corrected logger to reflect the source of hospital_filtered_docs_for_prompt
                                    logger.info(f"Selected {len(hospital_filtered_docs_for_prompt)} RAG snippets (from {len(all_retrieved_docs) if all_retrieved_docs else 0} initially retrieved by RAG invoke) for {current_rag_yaml_key}. Using top {len(temp_snippets)} in prompt.")
                            else:
                                if args.verbose:
                                    logger.info(f"No RAG snippets for {current_rag_yaml_key} after hospital-specific selection (initial RAG invoke count: {len(all_retrieved_docs) if all_retrieved_docs else 0}).")
                                retrieved_criteria_snippets_str = f"No RAG snippets specifically applicable to {target_campus_details['display_name_short']} were found after filtering."
                        except Exception as e_rag:
                            logger.error(f"Error during RAG retrieval for {current_rag_yaml_key}: {e_rag}")
                            retrieved_criteria_snippets_str = "Error during RAG retrieval process."
                    elif not exclusion_criteria_retriever: # This is the original retriever variable
                        if args.verbose:
                            logger.warning(f"Exclusion retriever not available for {current_rag_yaml_key}. Skipping RAG.")
                        retrieved_criteria_snippets_str = "Exclusion criteria retriever not available."
                    else: # Missing extracted_entities or specialty_needs
                        if args.verbose:
                            logger.info(f"Not enough info (entities/specialty_needs) to form RAG query for {current_rag_yaml_key}. Skipping RAG.")
                        retrieved_criteria_snippets_str = "Insufficient information to form RAG query."

                    # --- TEMP DEBUG: Print RAG snippets for this hospital ---
                    if args.verbose and retrieved_criteria_snippets_str and "No RAG snippets" not in retrieved_criteria_snippets_str and "Error during RAG" not in retrieved_criteria_snippets_str:
                        CONSOLE.print(Panel(retrieved_criteria_snippets_str, title=f"[bold yellow]Retrieved RAG Snippets for {target_campus_details['display_name_short']}[/bold yellow]", border_style="yellow", expand=False))
                    # --- END TEMP DEBUG ---

                    SYSTEM_MESSAGE_STEP3_INDIVIDUAL = """You are an expert transfer center physician. Your task is to evaluate a patient against the inclusion/exclusion criteria and current census data for a SINGLE specified hospital campus. Respond ONLY with a valid JSON object. Adhere strictly to the provided exclusion criteria. However, if you identify an edge case or have nuanced thoughts, use the 'llm_reasoning_notes' to explain your confidence level or provide 'food for thought'."""

                    USER_PROMPT_STEP3_INDIVIDUAL_TEMPLATE = """# Clinical Vignette Analysis - Step 3: Exclusion Criteria Evaluation (Individual Hospital)

You are an AI assistant helping to determine if a patient transfer to a specific hospital is appropriate
by evaluating exclusion criteria.

## Input Data:

### 1. Extracted Clinical Information:
{clinical_info}

### 2. Identified Specialty Needs:
{specialty_needs}

### 3. Exclusion Criteria for {hospital_name} (Applicable to {display_name}):
{exclusion_criteria_json}

### 3.5. Potentially Relevant Exclusion Criteria (Context from Knowledge Base):
{retrieved_criteria_snippets}

### 4. Current Census Data for {hospital_name}:
{census_data_json}

## Your Task:

Evaluate the patient against the provided information for {hospital_name}.

**Primary Source for Exclusion Criteria Adjudication:**
- If the "Exclusion Criteria for {hospital_name}" (Section 3 above) is empty or contains no criteria (this is the expected scenario), you MUST use the "Potentially Relevant Exclusion Criteria (Context from Knowledge Base)" (Section 3.5) as your list of criteria to adjudicate.
  - For each snippet listed in Section 3.5:
    - The text following the "- " (e.g., "- Patient must be less than 18 years of age.") is the `criterion_statement`.
    - Use the "Type" (e.g., general, departmental) and "Dept" (e.g., picu, N/A) from the snippet's header (e.g., "Snippet 1 (Source: ..., Type: general, Dept: N/A):") to categorize the criterion into the `general_criteria_adjudication` or `departmental_criteria_adjudication` list in your JSON output.
    - Determine if this `criterion_statement` is met for exclusion based on the "Extracted Clinical Information". Record this as `true` or `false` in `is_met_for_exclusion`.
    - Provide your specific reasoning in `reasoning_from_vignette`.
  - Your `general_criteria_adjudication` and `departmental_criteria_adjudication` lists in the JSON output MUST contain an entry for EACH criterion snippet processed from Section 3.5.

- If, unexpectedly, "Exclusion Criteria for {hospital_name}" (Section 3) is NOT empty, then meticulously evaluate EACH criterion from Section 3. You may use Section 3.5 for additional context in your `llm_reasoning_notes` in this specific case.

After this detailed adjudication, provide an `overall_transfer_decision`.
Finally, consider the "Current Census Data" to summarize potential census-related impacts in the `census_impact_summary`.

## Output Format (JSON):

Provide your response in the following JSON structure. Ensure all fields are populated.
When adjudicating from Section 3.5, the `criterion_statement` in your output MUST EXACTLY MATCH the text of the snippet (the part after "- ").

{{{{ # Note: Using double curlies to escape for f-string, then single for JSON
  "overall_transfer_decision": "Potentially Suitable" | "Likely Unsuitable" | "Unsuitable" | "Needs More Info" | "Error - Criteria Missing",
  "primary_exclusion_reasons": ["List of primary reasons if unsuitable, or 'No primary exclusion reasons identified.'"],
  "general_criteria_adjudication": [ // Should be an empty list [] if no relevant general RAG snippets from Section 3.5
    {{ // This is an EXAMPLE of ONE adjudicated general criterion
      "criterion_statement": "- Patient must be less than 18 years of age.", // EXACTLY copied from a RAG snippet in Section 3.5
      "is_met_for_exclusion": false, // Example: patient is 3yo, so this criterion does NOT exclude.
      "reasoning_from_vignette": "Patient is 3 years old, which is less than 18. This criterion is not met for exclusion."
    }},
    {{ // This is ANOTHER EXAMPLE
      "criterion_statement": "- Active bleeding requiring transfusion.", // EXACTLY copied from a RAG snippet
      "is_met_for_exclusion": true, // Example: vignette states 'patient has active GI bleed requiring PRBCs'.
      "reasoning_from_vignette": "Vignette mentions active GI bleed needing transfusions, so this criterion IS met for exclusion."
    }}
    // ... potentially more, one for EACH general RAG snippet from Section 3.5. If no general snippets, this list is [].
  ],
  "departmental_criteria_adjudication": [ // Should be an empty list [] if no relevant departmental RAG snippets
    {{ // This is an EXAMPLE of ONE adjudicated departmental criterion
      "department_name": "PICU", // From RAG snippet metadata or Section 3
      "criterion_statement": "- Requires ECMO capability.", // EXACTLY copied from a RAG snippet
      "is_met_for_exclusion": false, // Example: Vignette does not suggest ECMO is needed.
      "reasoning_from_vignette": "Patient's condition, while serious, does not currently indicate a need for ECMO based on the vignette."
    }}
    // ... potentially more, one for EACH departmental RAG snippet from Section 3.5. If no departmental snippets, this list is [].
  ],
  "census_impact_summary": {{
    "relevant_unit_type": "e.g., PICU, NICU, General Ward",
    "available_beds": "Number or 'N/A'",
    "notes": "Brief note on census impact, e.g., 'Sufficient beds available', 'Unit at capacity'."
  }},
  "llm_reasoning_notes": "Your overall reasoning, confidence, and any edge case considerations. If criteria are missing or unclear, state that here. This note should synthesize your findings from the detailed adjudication."
}}}}

## Important Notes on Criteria Application:

1.  **Strict Adherence and Completeness**:
    - If Section 3 (`exclusion_criteria_json`) is empty (expected scenario), you MUST evaluate EACH AND EVERY criterion snippet presented in Section 3.5 (`retrieved_criteria_snippets`). Use the text of the snippet (after "- ") as the `criterion_statement`.
    - If Section 3 is NOT empty (unexpected), you MUST evaluate EACH AND EVERY criterion presented in Section 3.
    - Adhere strictly to the exact wording. Do not infer, add, summarize, or skip any criteria you are evaluating. Your output adjudication lists must be comprehensive for the source you are using (primarily Section 3.5 or, if populated, Section 3).
2.  **Focus**: Your primary goal is to identify if *any* specific exclusion criterion (from the RAG snippets if Section 3 is empty) is met based on the vignette.
3.  **`is_met_for_exclusion`**: This field is CRITICAL.
    *   Set to `true` if the patient's condition/details from the vignette MATCH the exclusion criterion, meaning they SHOULD BE EXCLUDED based on this specific point.
    *   Set to `false` if the patient's condition/details DO NOT MATCH the exclusion criterion.
4.  **Clarity**: If criteria (from RAG snippets or Section 3) are ambiguous or seem to conflict, note this in "llm_reasoning_notes" AFTER attempting to adjudicate them as best as possible.
5.  **Missing Criteria**:
    - If Section 3 (`exclusion_criteria_json`) is empty AND Section 3.5 (`retrieved_criteria_snippets`) is also empty, indicates no snippets were found (e.g., contains text like "No snippets retrieved", "Error during RAG retrieval", or is simply empty), or is otherwise not usable for adjudication, THEN set `overall_transfer_decision` to "Error - Criteria Missing" and explain in `llm_reasoning_notes`.
    - Otherwise, proceed with adjudication using the available criteria (primarily from Section 3.5 if Section 3 is empty).
6.  **Specialized Hospitals**: While adhering strictly to provided criteria, if a hospital has an obvious primary specialty (e.g., women's health for PFW) and the patient clearly does not fit this specialty, this should be strongly reflected in your adjudication of relevant general criteria (likely from RAG snippets) and your `llm_reasoning_notes`.
7.  **Empty Adjudication Lists**: If Section 3.5 (`retrieved_criteria_snippets`) is empty, contains no usable snippets (e.g., 'No snippets retrieved', 'Error during RAG retrieval'), or if RAG retrieval failed, then both `general_criteria_adjudication` and `departmental_criteria_adjudication` lists in your JSON output MUST be empty lists (i.e., `[]`). Do NOT populate them with placeholder structures or example text in such cases.

Begin your detailed, criterion-by-criterion evaluation for {hospital_name}.
"""

                user_prompt_step3_individual = USER_PROMPT_STEP3_INDIVIDUAL_TEMPLATE.format(
                    clinical_info=json.dumps(extracted_entities, indent=2) if extracted_entities else "{}",
                    specialty_needs=json.dumps(specialty_needs, indent=2) if specialty_needs else "{}",
                    hospital_name=target_campus_details['campus_id'],  
                    display_name=target_campus_details['display_name'], 
                    exclusion_criteria_json=specific_exclusion_criteria_json,
                    retrieved_criteria_snippets=retrieved_criteria_snippets_str,
                    census_data_json=specific_census_data_json
                )

                step_3_individual_name = f"Step 3 Indiv. Eval - {target_campus_details['campus_id']}"
                individual_assessment = execute_llm_chat_completion(
                    client,
                    SYSTEM_MESSAGE_STEP3_INDIVIDUAL,
                    user_prompt_step3_individual,
                    step_name=step_3_individual_name
                )

                if individual_assessment:
                    if args.verbose:
                        logger.info(f"Successfully received individual assessment for {target_campus_details['campus_id']}")
                    all_individual_assessments[target_campus_details['campus_id']] = individual_assessment 
                    assessment_wrapper_for_consolidation = {"campus_id": target_campus_details['campus_id'], "evaluation": individual_assessment}
                    all_individual_assessment_objects_for_consolidation.append(assessment_wrapper_for_consolidation)
                    if args.verbose:
                        CONSOLE.print(f"[green]Individual assessment for {target_campus_details['campus_id']} completed.[/green]")
                else:
                    logger.error(f"Failed to get individual assessment for {target_campus_details['campus_id']}")
                    if args.verbose:
                        CONSOLE.print(f"[bold red]Failed individual assessment for {target_campus_details['campus_id']}. It will be excluded from final summary.[/bold red]")
                    failed_assessment_placeholder = {
                        "overall_transfer_decision": "Error - Evaluation Failed",
                        "primary_exclusion_reasons": ["LLM call for individual assessment failed."],
                        "llm_reasoning_notes": f"Could not complete evaluation for {target_campus_details['campus_id']} due to an error."
                    }
                    all_individual_assessments[target_campus_details['campus_id']] = failed_assessment_placeholder
                    all_individual_assessment_objects_for_consolidation.append({
                        "campus_id": target_campus_details['campus_id'],
                        "evaluation": failed_assessment_placeholder
                    })
            # After processing each hospital (successful or hardcoded exclusion):
            overall_progress.update(hospital_eval_task_id, advance=1)

        # After the loop, update the hospital eval task description and explicitly mark as completed.
        overall_progress.update(
            hospital_eval_task_id, 
            description=f"[plum4]All {hospital_eval_total} Hospitals Evaluated - Complete",
            completed=hospital_eval_total # Explicitly set completed count to total
        )

        overall_progress.advance(main_task) # Advance the main task for completing Step 3 (evaluations)

        # Step 4: Consolidate Assessments
        # No longer update main_task description here, Panel handles it.
        if args.verbose:
            CONSOLE.print(Panel("Step 4: Consolidating Assessments", style="bold blue"))
        if all_individual_assessment_objects_for_consolidation:
            SYSTEM_MESSAGE_STEP3_CONSOLIDATION = """You are an expert transfer center physician. You have been provided with individual evaluations for a patient against several hospital campuses. Your task is to consolidate these individual assessments into a single, comprehensive JSON object. The top-level keys of this object must be the campus_ids of the evaluated hospitals. Respond ONLY with a valid JSON object."""

            USER_PROMPT_STEP3_CONSOLIDATION_TEMPLATE = """Individual Hospital Evaluation Summaries:
{individual_evaluations_json_array}

Task:
Combine the provided individual hospital evaluations into a single JSON object. Each top-level key in the output JSON object must be the campus_id (e.g., "TCH_MAIN_TMC", "TCH_WOODLANDS", etc.) from the individual assessments, and its value should be the detailed evaluation object for that campus.

Example of final desired JSON structure:
{{{{ # Note: Using double curlies to escape for f-string, then single for JSON
  "TCH_MAIN_TMC": {{ ... evaluation for TCH_MAIN_TMC ... }},
  "TCH_WOODLANDS": {{ ... evaluation for TCH_WOODLANDS ... }},
  // ... other campuses ...
}}}}

Your Output (JSON only):
"""

            user_prompt_step3_consolidation = USER_PROMPT_STEP3_CONSOLIDATION_TEMPLATE.format(
                individual_evaluations_json_array=json.dumps(all_individual_assessment_objects_for_consolidation, indent=2)
            )
            
            exclusion_assessment = execute_llm_chat_completion(
                client,
                SYSTEM_MESSAGE_STEP3_CONSOLIDATION,
                user_prompt_step3_consolidation,
                step_name="Step 3 Consolidation"
            )
            
            if exclusion_assessment:
                if args.verbose:
                    logger.info(f"Successfully received consolidated assessment.")
                    CONSOLE.print("[green]Step 3: Exclusion Criteria Evaluation Completed.[/green]")
                display_consolidated_assessment_summary(exclusion_assessment, TARGET_HOSPITAL_KEYS, current_patient_vignette, extracted_entities, specialty_needs) # New function call
            else:
                logger.error("Failed to get consolidated assessment.")
                CONSOLE.print(Panel("[bold red]Step 3: Consolidation failed - No consolidated assessment received[/bold red]", border_style="red"))
                if all_individual_assessments:
                    logger.warning("Consolidation LLM call failed. Falling back to combined individual assessments.")
                    exclusion_assessment = all_individual_assessments 
                else:
                    exclusion_assessment = {"error": "Consolidation failed and no individual assessments available."}
        else:
            logger.error(f"No individual assessments available for consolidation in Step 3.")
            CONSOLE.print(Panel("[bold red]Step 3: Consolidation failed - No individual assessments to process[/bold red]", border_style="red"))
            
        overall_progress.advance(main_task)

        # Step 4: Final Care Destination Recommendation
        overall_progress.update(main_task, advance=1, description="Step 4: Generating Final Recommendation")
        
        final_recommendation_panel_title = "[bold cyan]Final Recommendation[/bold cyan]"
        final_recommendation_str = "No recommendation could be generated at this time."
        
        sending_location_coords = None
        if args.current_location:
            if args.verbose:
                CONSOLE.print(f"Geocoding sending location: {args.current_location}...", style="dim")
            # Use the main geolocator, hospital_cache in hospital_search_client is for TCH campuses primarily
            sending_location_obj = get_location(args.current_location, {}, geolocator) 
            if sending_location_obj:
                sending_location_coords = (sending_location_obj.latitude, sending_location_obj.longitude)
                if args.verbose:
                    CONSOLE.print(f"Sending location '{args.current_location}' geocoded to: {sending_location_coords}", style="dim green")
            else:
                if args.verbose:
                    CONSOLE.print(f"Could not geocode sending location: {args.current_location}", style="dim red")
                final_recommendation_str = f"Could not determine distances: Sending location '{args.current_location}' could not be geocoded."
                final_recommendation_panel_title = "[bold yellow]Final Recommendation[/bold yellow]"
        else:
            if args.verbose:
                CONSOLE.print("No sending location provided. Cannot calculate distances for recommendation.", style="dim yellow")
            final_recommendation_str = "Cannot calculate distances: Sending location not provided."
            final_recommendation_panel_title = "[bold yellow]Final Recommendation[/bold yellow]"

        if sending_location_coords: # Proceed only if we have coordinates for the sending location
            suitable_hospitals_with_distances = []
            acceptable_decisions = ["Accept", "Consider for Transfer"] # Define what's "suitable"
            
            for hospital_assessment_wrapper in all_individual_assessment_objects_for_consolidation:
                campus_id = hospital_assessment_wrapper['campus_id']
                evaluation = hospital_assessment_wrapper['evaluation']
                decision = evaluation.get("overall_transfer_decision")

                if decision in acceptable_decisions:
                    target_campus_info = None
                    for _, details in TARGET_HOSPITAL_KEYS.items(): # TARGET_HOSPITAL_KEYS is already populated with TCH locations
                        if details['campus_id'] == campus_id:
                            target_campus_info = details
                            break
                    
                    if target_campus_info and 'latitude' in target_campus_info and 'longitude' in target_campus_info:
                        tch_campus_coords = (target_campus_info['latitude'], target_campus_info['longitude'])
                        try:
                            distance_miles = geodesic(sending_location_coords, tch_campus_coords).miles
                            suitable_hospitals_with_distances.append({
                                "campus_id": campus_id,
                                "display_name_short": target_campus_info.get('display_name_short', campus_id),
                                "decision": decision,
                                "distance_miles": distance_miles,
                                "primary_reason": evaluation.get("primary_reason_for_decision", "N/A")
                            })
                        except Exception as e_dist:
                            if args.verbose:
                                CONSOLE.print(f"Error calculating distance for {campus_id}: {e_dist}", style="dim red")
                    elif args.verbose:
                        CONSOLE.print(f"Could not find coordinates for suitable campus {campus_id} to calculate distance.", style="dim yellow")

            if suitable_hospitals_with_distances:
                suitable_hospitals_with_distances.sort(key=lambda x: x['distance_miles'])
                recommended_campus_details = suitable_hospitals_with_distances[0]
                
                final_recommendation_str = (
                    f"Recommended Campus: [bold green]{recommended_campus_details['display_name_short']}[/bold green]\n"
                    f"Distance: {recommended_campus_details['distance_miles']:.1f} miles\n"
                    f"Basis: {recommended_campus_details['decision']} - {recommended_campus_details['primary_reason']}"
                )
                final_recommendation_panel_title = "[bold green]Final Recommendation[/bold green]"

                if args.verbose and len(suitable_hospitals_with_distances) > 1:
                    other_options_str = "\n\n[u]Other suitable options (further away):[/u]\n"
                    for i, hosp in enumerate(suitable_hospitals_with_distances[1:3]): # Show next up to 2
                         other_options_str += f"  {i+2}. {hosp['display_name_short']} ({hosp['distance_miles']:.1f} miles) - {hosp['decision']}: {hosp['primary_reason']}\n"
                    final_recommendation_str += other_options_str.rstrip()
            elif final_recommendation_str == "No recommendation could be generated at this time.": # Only update if not already set by geocoding issue
                final_recommendation_str = "No TCH campuses were identified as 'Accept' or 'Consider for Transfer' based on the evaluation."
                final_recommendation_panel_title = "[bold yellow]Final Recommendation[/bold yellow]"
        
        CONSOLE.print(Panel(Text(final_recommendation_str, justify="left"), title=final_recommendation_panel_title, border_style=final_recommendation_panel_title.split(' ')[0][1:], expand=False))
        overall_progress.update(main_task, advance=1, description="Step 4: Final Recommendation Complete")

    CONSOLE.print("\nTransfer Center Analysis Complete.")

if __name__ == '__main__':
    main()
