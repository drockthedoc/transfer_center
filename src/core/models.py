"""
Defines the Pydantic data models used throughout the application.

These models ensure data validation and provide a clear structure for various
entities such as patient data, hospital campus details, transfer requests,
and recommendations.
"""
from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class Location(BaseModel):
    """Represents a geographical location with latitude and longitude."""
    latitude: float = Field(..., description="Latitude in decimal degrees.", ge=-90.0, le=90.0)
    longitude: float = Field(..., description="Longitude in decimal degrees.", ge=-180.0, le=180.0)

class PatientData(BaseModel):
    """Holds all relevant data pertaining to a patient for transfer consideration."""
    patient_id: str = Field(..., description="Unique identifier for the patient.", min_length=1)
    chief_complaint: str = Field(..., description="The patient's primary reason for seeking medical attention.")
    clinical_history: str = Field(..., description="Relevant clinical history of the patient.")
    vital_signs: Dict[str, str] = Field(default_factory=dict, description="Patient's vital signs, e.g., {'hr': '80', 'bp': '120/80'}.")
    labs: Dict[str, str] = Field(default_factory=dict, description="Relevant lab results, e.g., {'troponin': '0.01 ng/mL'}.")
    current_location: Location = Field(..., description="Patient's current geographical location.")

class CampusExclusion(BaseModel):
    """Defines an exclusion criterion for a hospital campus."""
    criteria_id: str = Field(..., description="Unique identifier for the exclusion criterion.", min_length=1)
    criteria_name: str = Field(..., description="Short name for the exclusion criterion (e.g., 'No Burn Unit').")
    description: str = Field(..., description="Detailed description of the exclusion.")
    affected_keywords_in_complaint: List[str] = Field(default_factory=list, description="Keywords in chief complaint that trigger this exclusion.")
    affected_keywords_in_history: List[str] = Field(default_factory=list, description="Keywords in clinical history that trigger this exclusion.")

class MetroArea(str, Enum):
    """Enumeration of metropolitan areas served."""
    HOUSTON = "HOUSTON_METRO"
    AUSTIN = "AUSTIN_METRO"

class BedCensus(BaseModel):
    """Represents the bed availability status for various types of beds in a hospital."""
    total_beds: int = Field(..., description="Total number of general beds.", ge=0)
    available_beds: int = Field(..., description="Number of available general beds.", ge=0)
    icu_beds_total: int = Field(..., description="Total number of ICU beds (includes PICU).", ge=0)
    icu_beds_available: int = Field(..., description="Number of available ICU beds (includes PICU).", ge=0)
    nicu_beds_total: int = Field(..., description="Total number of NICU beds.", ge=0)
    nicu_beds_available: int = Field(..., description="Number of available NICU beds.", ge=0)

class HelipadData(BaseModel):
    """Represents data for a single helipad at a hospital campus."""
    helipad_id: str = Field(..., description="Unique identifier for the helipad.", min_length=1)
    name: Optional[str] = Field(None, description="Optional descriptive name for the helipad.")
    location: Location = Field(..., description="Geographical location of the helipad.")

class HospitalCampus(BaseModel):
    """
    Represents a single hospital campus and all its relevant attributes
    for decision-making, including location, bed census, exclusions, and helipads.
    """
    campus_id: str = Field(..., description="Unique identifier for the hospital campus.", min_length=1)
    name: str = Field(..., description="Full name of the hospital campus.")
    metro_area: MetroArea = Field(..., description="Metropolitan area where the campus is located.")
    address: str = Field(..., description="Street address of the campus.")
    location: Location = Field(..., description="Geographical location of the main campus building.")
    exclusions: List[CampusExclusion] = Field(default_factory=list, description="List of exclusion criteria for this campus.")
    bed_census: BedCensus = Field(..., description="Current bed census data for the campus.")
    helipads: List[HelipadData] = Field(default_factory=list, description="List of helipads available at the campus.")

class TransportMode(str, Enum):
    """Enumeration of available transport modes."""
    GROUND_AMBULANCE = "GROUND_AMBULANCE"
    AIR_AMBULANCE = "AIR_AMBULANCE" # Helicopter or fixed-wing

class WeatherData(BaseModel):
    """Contains current weather information relevant for transport decisions."""
    temperature_celsius: float = Field(..., description="Current temperature in Celsius.")
    wind_speed_kph: float = Field(..., description="Wind speed in kilometers per hour.", ge=0)
    precipitation_mm_hr: float = Field(..., description="Precipitation rate in millimeters per hour.", ge=0)
    visibility_km: float = Field(..., description="Visibility in kilometers.", ge=0)
    adverse_conditions: List[str] = Field(default_factory=list, description="List of any adverse weather conditions (e.g., 'FOG', 'THUNDERSTORM').")

class TransferRequest(BaseModel):
    """
    Encapsulates all information related to a single patient transfer request,
    including patient data, sending facility details, and transport preferences.
    """
    request_id: str = Field(..., description="Unique identifier for the transfer request.", min_length=1)
    patient_data: PatientData = Field(..., description="Detailed data for the patient being transferred.")
    sending_facility_name: str = Field(..., description="Name of the facility initiating the transfer.")
    sending_facility_location: Location = Field(..., description="Geographical location of the sending facility.")
    preferred_transport_mode: Optional[TransportMode] = Field(None, description="Preferred transport mode, if any.")

class Recommendation(BaseModel):
    """Represents the final recommendation provided by the decision engine."""
    transfer_request_id: str = Field(..., description="Identifier of the original transfer request.")
    recommended_campus_id: str = Field(..., description="Identifier of the recommended hospital campus.")
    reason: str = Field(..., description="Brief summary of why this campus was chosen.")
    confidence_score: Optional[float] = Field(None, description="Numerical score indicating the strength of the recommendation (0-100).")
    explainability_details: Optional[Dict] = Field(None, description="Detailed factors contributing to the recommendation.")
    notes: List[str] = Field(default_factory=list, description="Comprehensive log of notes from the decision-making process.")

# Pydantic v2 automatically handles forward references like List["HelipadData"]
# if they are defined as string literals in type hints.
# No explicit update_forward_refs() call is needed.
