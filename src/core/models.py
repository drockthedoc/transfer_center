"""
Defines the Pydantic data models used throughout the application.

These models ensure data validation and provide a clear structure for various
entities such as patient data, hospital campus details, transfer requests,
and recommendations.
"""

from datetime import datetime
from enum import Enum
import math
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, FieldValidationInfo


class Location(BaseModel):
    """Represents a geographical location with latitude and longitude."""

    latitude: float = Field(
        ..., description="Latitude in decimal degrees.", ge=-90.0, le=90.0
    )
    longitude: float = Field(
        ..., description="Longitude in decimal degrees.", ge=-180.0, le=180.0
    )


class PatientData(BaseModel):
    """Holds all relevant data pertaining to a patient for transfer consideration."""

    patient_id: str = Field(
        ..., description="Unique identifier for the patient.", min_length=1
    )
    # Original fields are now optional with defaults or can be derived from other fields
    chief_complaint: Optional[str] = Field(
        default="",
        description="The patient's primary reason for seeking medical attention.",
    )
    clinical_history: Optional[str] = Field(
        default="", description="Relevant clinical history of the patient."
    )
    vital_signs: Dict[str, str] = Field(
        default_factory=dict,
        description="Patient's vital signs, e.g., {'hr': '80', 'bp': '120/80'}.",
    )
    labs: Dict[str, str] = Field(
        default_factory=dict,
        description="Relevant lab results, e.g., {'troponin': '0.01 ng/mL'}.",
    )
    current_location: Optional[Location] = Field(
        default=None, description="Patient's current geographical location."
    )

    # Fields actually used in the application
    clinical_text: str = Field(
        default="", description="Raw clinical text entered by the user."
    )
    extracted_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Data extracted from clinical text by LLM or rule-based processing.",
    )
    care_needs: List[str] = Field(
        default_factory=list,
        description="List of care needs identified for the patient.",
    )
    care_level: str = Field(
        default="General",
        description="Recommended care level (General, ICU, PICU, NICU, etc.).",
    )


class CampusExclusion(BaseModel):
    """Defines an exclusion criterion for a hospital campus."""

    criteria_id: str = Field(
        ..., description="Unique identifier for the exclusion criterion.", min_length=1
    )
    criteria_name: str = Field(
        ...,
        description="Short name for the exclusion criterion (e.g., 'No Burn Unit').",
    )
    name: Optional[str] = Field(
        None,
        description="Alternative name field for the exclusion criterion.",
    )
    description: str = Field(..., description="Detailed description of the exclusion.")
    affected_keywords_in_complaint: List[str] = Field(
        default_factory=list,
        description="Keywords in chief complaint that trigger this exclusion.",
    )
    affected_keywords_in_history: List[str] = Field(
        default_factory=list,
        description="Keywords in clinical history that trigger this exclusion.",
    )
    min_age: Optional[int] = Field(
        None,
        description="Minimum patient age (in years) for this exclusion to apply.",
    )
    max_age: Optional[int] = Field(
        None, description="Maximum patient age (in years) for this exclusion to apply."
    )
    min_weight: Optional[float] = Field(
        None, description="Minimum patient weight (in kg) for this exclusion to apply."
    )
    max_weight: Optional[float] = Field(
        None, description="Maximum patient weight (in kg) for this exclusion to apply."
    )
    excluded_care_levels: List[str] = Field(
        default_factory=list,
        description="List of care levels excluded by this criterion.",
    )
    excluded_conditions: List[str] = Field(
        default_factory=list,
        description="List of medical conditions excluded by this criterion.",
    )


class MetroArea(str, Enum):
    """Enumeration of metropolitan areas served."""

    HOUSTON = "HOUSTON_METRO"
    AUSTIN = "AUSTIN_METRO"


class BedCensus(BaseModel):
    """Represents the bed availability status for various types of beds in a hospital."""

    total_beds: int = Field(..., description="Total number of general beds.", ge=0)
    available_beds: int = Field(
        ..., description="Number of available general beds.", ge=0
    )
    icu_beds_total: int = Field(
        ..., description="Total number of ICU beds (includes PICU).", ge=0
    )
    icu_beds_available: int = Field(
        ..., description="Number of available ICU beds (includes PICU).", ge=0
    )
    nicu_beds_total: int = Field(..., description="Total number of NICU beds.", ge=0)
    nicu_beds_available: int = Field(
        ..., description="Number of available NICU beds.", ge=0
    )


class HelipadData(BaseModel):
    """Represents data for a single helipad at a hospital campus."""

    helipad_id: str = Field(
        ..., description="Unique identifier for the helipad.", min_length=1
    )
    name: Optional[str] = Field(
        None, description="Optional descriptive name for the helipad."
    )
    location: Location = Field(..., description="Geographical location of the helipad.")


class CareLevel(str, Enum):
    """Standardized care levels available at hospital campuses."""
    
    GENERAL = "General"
    ICU = "ICU"  # Intensive Care Unit
    PICU = "PICU"  # Pediatric Intensive Care Unit
    NICU = "NICU"  # Neonatal Intensive Care Unit
    TRAUMA = "Trauma"  # Trauma care
    BURN = "Burn"  # Burn unit
    STROKE = "Stroke"  # Stroke center
    CARDIAC = "Cardiac"  # Cardiac care


class Specialty(str, Enum):
    """Standardized medical specialties available at hospital campuses."""
    
    GENERAL_MEDICINE = "General Medicine"
    PEDIATRICS = "Pediatrics"
    NEONATOLOGY = "Neonatology"
    CARDIOLOGY = "Cardiology"
    NEUROLOGY = "Neurology"
    ORTHOPEDICS = "Orthopedics"
    BURN_CARE = "Burn Care"
    TRAUMA_SURGERY = "Trauma Surgery"
    ONCOLOGY = "Oncology"
    PSYCHIATRY = "Psychiatry"


class HospitalCampus(BaseModel):
    """Represents a single hospital campus and all its relevant attributes
    for decision-making, including location, bed census, exclusions, and helipads."""

    campus_id: str = Field(
        ..., description="Unique identifier for the hospital campus.", min_length=1
    )
    name: str = Field(..., description="Name of the hospital campus.")
    location: Location = Field(..., description="Geographical location of the campus.")
    metro_area: Optional[MetroArea] = Field(
        None, description="Metropolitan area this campus belongs to."
    )
    exclusions: List[CampusExclusion] = Field(
        default_factory=list,
        description="List of exclusion criteria for this campus.",
    )
    bed_census: BedCensus = Field(
        ..., description="Current bed census data for the campus."
    )
    helipads: List[HelipadData] = Field(
        default_factory=list, description="List of helipads available at the campus."
    )
    care_levels: List[CareLevel] = Field(
        default_factory=list, description="Care levels available at this campus."
    )
    specialties: List[Specialty] = Field(
        default_factory=list, description="Medical specialties available at this campus."
    )
    is_pediatric_hospital: bool = Field(
        default=False, description="Whether this is a dedicated pediatric hospital."
    )
    address: Optional[str] = Field(
        default=None, description="Physical address of the hospital campus."
    )
    phone: Optional[str] = Field(
        default=None, description="Main contact phone number for the hospital."
    )
    website: Optional[str] = Field(
        default=None, description="Hospital website URL."
    )
    
    def calculate_distance(self, other_location: Location) -> float:
        """Calculate the straight-line distance in kilometers to another location using the Haversine formula."""
        # Earth's radius in kilometers
        earth_radius = 6371.0
        
        # Convert latitude and longitude from degrees to radians
        lat1 = math.radians(self.location.latitude)
        lon1 = math.radians(self.location.longitude)
        lat2 = math.radians(other_location.latitude)
        lon2 = math.radians(other_location.longitude)
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = earth_radius * c
        
        return distance
    
    def calculate_driving_distance_km(self, other_location: Location) -> float:
        """Estimate driving distance in kilometers using a simple approximation factor on the straight-line distance.
        
        This is a rough estimate. For accurate routing, an external mapping API should be used.
        """
        # Driving distance is typically 20-30% longer than straight-line distance
        # Using a factor of 1.3 as a reasonable approximation
        straight_line_distance = self.calculate_distance(other_location)
        return straight_line_distance * 1.3
    
    def estimate_driving_time_minutes(self, other_location: Location, traffic_factor: float = 1.0) -> int:
        """Estimate driving time in minutes based on approximated driving distance.
        
        Args:
            other_location: The destination location
            traffic_factor: Multiplier for traffic conditions (1.0 = normal, 1.5 = moderate traffic, 2.0 = heavy traffic)
            
        Returns:
            Estimated driving time in minutes
        """
        # Use a more realistic average driving speed of 75 km/h (1.25 km/minute)
        # for long distances between cities
        driving_distance = self.calculate_driving_distance_km(other_location)
        driving_speed_km_per_minute = 75 / 60  # 75 km/h converted to km/minute
        
        # Calculate time and apply traffic factor
        time_minutes = (driving_distance / driving_speed_km_per_minute) * traffic_factor
        
        # Round to nearest minute
        return round(time_minutes)
    
    def has_care_level(self, care_level: str) -> bool:
        """Check if this campus provides a specific care level."""
        if not self.care_levels:
            return False
        
        # Handle both string and enum input
        if isinstance(care_level, str):
            return any(level.value == care_level for level in self.care_levels) or any(level == care_level for level in self.care_levels)
        return care_level in self.care_levels
    
    def has_specialty(self, specialty: str) -> bool:
        """Check if this campus provides a specific medical specialty."""
        if not self.specialties:
            return False
            
        # Handle both string and enum input
        if isinstance(specialty, str):
            return any(spec.value == specialty for spec in self.specialties) or any(spec == specialty for spec in self.specialties)
        return specialty in self.specialties


class TransportMode(str, Enum):
    """Enumeration of available transport modes."""

    GROUND_AMBULANCE = "GROUND_AMBULANCE"
    AIR_AMBULANCE = "AIR_AMBULANCE"  # Generic air transport
    HELICOPTER = "HELICOPTER"  # Specific helicopter transport
    FIXED_WING = "FIXED_WING"  # Specific fixed-wing aircraft transport


class BedAvailability(BaseModel):
    """Represents the availability of a specific type of bed at a campus."""
    campus_id: str = Field(..., description="Identifier for the campus.")
    bed_type: str = Field(..., description="Type of bed (e.g., General, PICU, NICU).")
    available_beds: int = Field(..., description="Number of available beds of this type.", ge=0)
    last_updated: Optional[str] = Field(None, description="Timestamp of when this data was last updated.")


class ScoringResult(BaseModel):
    """Represents the result from a clinical scoring system."""
    scorer_name: str = Field(..., description="Name of the scoring system used (e.g., PEWS, TRAP).")
    score_value: Optional[Any] = Field(None, description="The primary numerical score or categorical result.")
    interpretation: Optional[str] = Field(None, description="Textual interpretation of the score.")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional structured data specific to the scorer (e.g., sub-scores, risk levels).")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of when the score was calculated.")


class TransportOption(BaseModel):
    """Represents a single transport option with mode and estimated time."""
    mode: TransportMode = Field(..., description="The mode of transport.")
    estimated_time_minutes: float = Field(..., description="Estimated travel time in minutes.", ge=0)
    cost: Optional[float] = Field(None, description="Estimated cost of this transport option.", ge=0)
    availability_details: Optional[str] = Field(None, description="Notes on the availability of this transport option.")


class WeatherData(BaseModel):
    """Contains current weather information relevant for transport decisions."""

    # Support both naming conventions for temperature
    temperature_celsius: Optional[float] = Field(
        None, description="Current temperature in Celsius."
    )
    temperature_c: Optional[float] = Field(
        None, description="Current temperature in Celsius (alternative field name)."
    )
    wind_speed_kph: float = Field(
        ..., description="Wind speed in kilometers per hour.", ge=0
    )
    precipitation_mm_hr: Optional[float] = Field(
        default=0.0, description="Precipitation rate in millimeters per hour.", ge=0
    )
    visibility_km: float = Field(..., description="Visibility in kilometers.", ge=0)
    weather_condition: Optional[str] = Field(
        default="Clear", description="General weather condition description."
    )
    adverse_conditions: List[str] = Field(
        default_factory=list,
        description="List of any adverse weather conditions (e.g., 'FOG', 'THUNDERSTORM').",
    )

    @field_validator("temperature_celsius", mode='before')
    @classmethod
    def set_temp_celsius(cls, v, info: FieldValidationInfo):
        """Ensure temperature_celsius is set from temperature_c if not provided."""
        if v is None and info.data and "temperature_c" in info.data and info.data["temperature_c"] is not None:
            return info.data["temperature_c"]
        return v

    @field_validator("temperature_c", mode='before')
    @classmethod
    def set_temp_c(cls, v, info: FieldValidationInfo):
        """Ensure temperature_c is set from temperature_celsius if not provided."""
        if v is None and info.data and "temperature_celsius" in info.data and info.data["temperature_celsius"] is not None:
            return info.data["temperature_celsius"]
        return v


class TransferRequest(BaseModel):
    """
    Encapsulates all information related to a single patient transfer request,
    including patient data, sending facility details, and transport preferences.
    """

    request_id: str = Field(
        ..., description="Unique identifier for the transfer request.", min_length=1
    )
    patient_data: PatientData = Field(
        ..., description="Detailed data for the patient being transferred."
    )
    # Make these optional with default values to maintain backward compatibility
    sending_facility_name: Optional[str] = Field(
        default="Unknown Facility",
        description="Name of the facility initiating the transfer.",
    )
    # New field that matches the actual usage in the code
    sending_location: Location = Field(
        ..., description="Geographical location of the sending facility."
    )
    # Add other fields that are used in the code
    requested_datetime: Optional[datetime] = Field(
        default_factory=datetime.now,
        description="Date and time when the transfer was requested.",
    )
    transport_mode: Optional[TransportMode] = Field(
        default=None, description="Selected transport mode for this transfer."
    )
    transport_info: Dict[str, Any] = Field(
        default_factory=dict, description="Additional transport-related information."
    )
    preferred_transport_mode: Optional[TransportMode] = Field(
        None, description="Preferred transport mode, if any."
    )
    processed_scoring_results: List[ScoringResult] = Field(
        default_factory=list, description="List of processed ScoringResult objects."
    )
    
    # Property accessors for transport_info dictionary values
    @property
    def clinical_text(self) -> str:
        """Get the clinical text from transport_info dictionary."""
        return self.transport_info.get("clinical_text", "")
    
    @clinical_text.setter
    def clinical_text(self, value: str) -> None:
        """Set the clinical text in transport_info dictionary."""
        self.transport_info["clinical_text"] = value
    
    @property
    def scoring_results(self) -> Dict[str, Any]:
        """Get the scoring results from transport_info dictionary."""
        return self.transport_info.get("scoring_results", {})
    
    @scoring_results.setter
    def scoring_results(self, value: Dict[str, Any]) -> None:
        """Set the scoring results in transport_info dictionary."""
        self.transport_info["scoring_results"] = value
    
    @property
    def human_suggestions(self) -> Dict[str, Any]:
        """Get the human suggestions from transport_info dictionary."""
        return self.transport_info.get("human_suggestions", {})
    
    @human_suggestions.setter
    def human_suggestions(self, value: Dict[str, Any]) -> None:
        """Set the human suggestions in transport_info dictionary."""
        self.transport_info["human_suggestions"] = value
    
    # Backward compatibility for sending_facility_location
    @property
    def sending_facility_location(self) -> Optional[Location]:
        """For backward compatibility, returns sending_location."""
        return self.sending_location
    
    @sending_facility_location.setter
    def sending_facility_location(self, value: Optional[Location]) -> None:
        """For backward compatibility, sets sending_location."""
        if value is not None:
            self.sending_location = value
    
    @field_validator("transport_info", mode='before')
    @classmethod
    def ensure_transport_info(cls, v):
        """Ensure transport_info is always a dictionary."""
        if v is None:
            return {}
        return v
    
    def get_transport_info_value(self, key: str, default: Any = None) -> Any:
        """Safely get a value from transport_info with a default if not present."""
        try:
            return self.transport_info.get(key, default)
        except (AttributeError, TypeError):
            return default
    
    def set_transport_info_value(self, key: str, value: Any) -> None:
        """Safely set a value in transport_info dictionary."""
        if self.transport_info is None:
            self.transport_info = {}
        self.transport_info[key] = value


class Recommendation(BaseModel):
    """Represents the final recommendation provided by the decision engine."""

    transfer_request_id: str = Field(
        ..., description="Identifier of the original transfer request."
    )
    recommended_campus_id: str = Field(
        ..., description="Identifier of the recommended hospital campus."
    )
    recommended_campus_name: str = Field(
        default="", description="Name of the recommended hospital campus."
    )
    reason: str = Field(..., description="Brief summary of why this campus was chosen.")
    confidence_score: Optional[float] = Field(
        default=0.0,
        description="Numerical score indicating the strength of the recommendation (0-100).",
        ge=0.0,
        le=100.0
    )
    recommended_level_of_care: str = Field(
        default="General",
        description="Recommended level of care (General, ICU, PICU, NICU, etc.)."
    )
    transport_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Details about transport including mode, ETA, and special considerations."
    )
    conditions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Current conditions affecting transport such as weather and traffic."
    )
    explainability_details: "LLMReasoningDetails" = Field(
        default_factory=lambda: LLMReasoningDetails(main_recommendation_reason="No specific reason provided."),
        description="Detailed LLM reasoning contributing to the recommendation."
    )
    notes: List[str] = Field(
        default_factory=list,
        description="Comprehensive log of notes from the decision-making process.",
    )
    simple_explanation: Dict[str, Any] = Field(
        default_factory=dict,
        description="A basic, rule-based explanation for the recommendation."
    )
    final_travel_time_minutes: Optional[float] = Field(None, description="Final calculated travel time in minutes for the recommended option.")
    chosen_transport_mode: Optional[str] = Field(None, description="The transport mode chosen for the recommendation.")
    scoring_results: List[ScoringResult] = Field(default_factory=list, description="List of scoring results considered.")
    
    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, v):
        """Ensure confidence score is a valid percentage."""
        if v is None:
            return 0.0
        if not 0.0 <= v <= 100.0:
            raise ValueError("Confidence score must be between 0.0 and 100.0")
        return float(v)
    
    @field_validator("explainability_details", mode='before')
    @classmethod
    def ensure_explainability_details(cls, v):
        if v is None:
            return LLMReasoningDetails(main_recommendation_reason="No LLM reasoning provided.")
        if isinstance(v, LLMReasoningDetails):
            return v
        if isinstance(v, dict):
            # Attempt to gracefully handle old structure vs new structure.
            # If 'main_recommendation_reason' is present, assume it's new.
            # Otherwise, provide a default for the new required field.
            if "main_recommendation_reason" not in v and \
               any(k in v for k in ["factors_considered", "alternative_options", "decision_points", "score_utilization", "distance_factors", "exclusion_reasons"]):
                # This looks like the old dictionary structure.
                return LLMReasoningDetails(
                    main_recommendation_reason="Primary reason not specified in new format.",
                    key_factors_considered=v.get("factors_considered", []),
                )
            try:
                return LLMReasoningDetails(**v)
            except Exception:  # Broad exception to catch Pydantic errors during parsing
                # If parsing fails (e.g. missing main_recommendation_reason in a dict that's not the old format)
                return LLMReasoningDetails(main_recommendation_reason="Could not parse LLM reasoning.")
        # If it's some other incompatible type, return a default.
        return LLMReasoningDetails(main_recommendation_reason="Invalid LLM reasoning format.")

    @property
    def has_transport_weather_info(self) -> bool:
        """Check if the recommendation has weather information for transport."""
        return bool(self.conditions.get("weather", {}))
    
    @property
    def has_transport_traffic_info(self) -> bool:
        """Check if the recommendation has traffic information for transport."""
        return bool(self.conditions.get("traffic", {}))
    
    def get_travel_time_estimate(self) -> str:
        """Get the estimated travel time as a formatted string."""
        if not self.transport_details.get("estimated_time_minutes"):
            return "Unknown"
        
        minutes = self.transport_details.get("estimated_time_minutes", 0)
        hours, minutes = divmod(minutes, 60)
        
        if hours > 0:
            return f"{hours} hr {minutes} min"
        return f"{minutes} min"
    
    def infer_recommended_level_of_care(self, patient_data: PatientData) -> str:
        """Infer the recommended level of care if not explicitly set."""
        # If already set, return it
        if self.recommended_level_of_care and self.recommended_level_of_care != "General":
            return self.recommended_level_of_care
        
        # Try to infer from patient data
        if patient_data.care_level and patient_data.care_level != "General":
            self.recommended_level_of_care = patient_data.care_level
            return self.recommended_level_of_care
            
        # Try to infer from explainability details
        if hasattr(self, 'explainability_details') and self.explainability_details:
            # Check main recommendation reason
            if hasattr(self.explainability_details, 'main_recommendation_reason') and self.explainability_details.main_recommendation_reason:
                reason = self.explainability_details.main_recommendation_reason.upper()
                if "PICU" in reason:
                    return "PICU"
                if "NICU" in reason:
                    return "NICU"
                if "ICU" in reason or "INTENSIVE" in reason:
                    return "ICU"
                
            # Check key factors
            if hasattr(self.explainability_details, 'key_factors_considered') and self.explainability_details.key_factors_considered:
                for factor in self.explainability_details.key_factors_considered:
                    if isinstance(factor, str):
                        factor_upper = factor.upper()
                        if "PICU" in factor_upper:
                            return "PICU"
                        if "NICU" in factor_upper:
                            return "NICU"
                        if "ICU" in factor_upper or "INTENSIVE" in factor_upper:
                            return "ICU"
        
        return self.recommended_level_of_care or "General"


class LLMReasoningDetails(BaseModel):
    """Standardized schema for LLM reasoning and explainability."""

    main_recommendation_reason: str = Field(
        ..., description="Primary reason for the top recommendation."
    )
    alternative_reasons: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Reasons why other hospitals were considered but not chosen, mapping hospital ID/name to reason string.",
    )
    key_factors_considered: Optional[List[str]] = Field(
        default_factory=list,
        description="Key factors LLM considered (e.g., 'distance', 'specialty_match').",
    )
    confidence_explanation: Optional[str] = Field(
        None, description="Brief explanation of the confidence score, if available."
    )

    # Ensure that default_factory is used correctly for mutable types
    @field_validator("alternative_reasons", "key_factors_considered", mode='before')
    @classmethod
    def ensure_defaults(cls, v, info):
        if v is None:
            # For Pydantic v2, we'll just return empty defaults
            if info.field_name == "alternative_reasons":
                return {}
            elif info.field_name == "key_factors_considered":
                return []
        return v


# Pydantic v2 automatically handles forward references like List["HelipadData"]
# and "LLMReasoningDetails" if they are defined as string literals in type hints
# or if the class is already defined before being referenced.
# No explicit update_forward_refs() call is needed if LLMReasoningDetails is defined before Recommendation,
# or if "LLMReasoningDetails" is used as a string hint.
# For clarity and to avoid potential issues with linters/type checkers if order changes,
# it's often good practice to define models before they are referenced directly by type
# or use forward references (string literals for type hints).

# If Recommendation is defined before LLMReasoningDetails, you might need:
# Recommendation.update_forward_refs()
# However, with Pydantic v2 and the current ordering (LLMReasoningDetails after Recommendation,
# but type hint is a string "LLMReasoningDetails"), this should be handled.
# Let's ensure LLMReasoningDetails is defined before it's used or use string consistently.
# The provided code uses a string hint, which is fine.
