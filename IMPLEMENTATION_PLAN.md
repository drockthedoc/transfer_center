# Transfer Center Implementation Plan

This document provides a sophisticated, trackable, and detailed implementation strategy for the Transfer Center application, covering all checklist items with concrete steps and automated testing strategies.

## Implementation Priority Order

1. **Core Data Model Fixes** - *Critical priority*: Fix fundamental data structure issues first
2. **Core Decision Support & Explainability** - *Highest priority*: Enhance reasoning display and scoring transparency
3. **Map & Visualization Enhancements** - Improve geographic representation and distance factors
4. **Responsive UI and Workflow Improvements** - Enhance user experience and application responsiveness
5. **Focused Pediatric Scoring Implementation** - Implement specialized clinical scoring systems
6. **Streamlined LLM Integration** - Optimize prompt engineering and response handling

## 1. Core Data Model Fixes (Critical Priority)

### Implementation Plan: TransferRequest Model

**Status: Completed**

#### Step 1: Refactor TransferRequest Class
- **Status: Completed**
- Refined the `TransferRequest` class to properly utilize the `transport_info` dictionary for extended data.
- Implemented proper property accessors (getters and setters) for `clinical_text`, `scoring_results`, and `human_suggestions`.
- Validation for required fields is handled by Pydantic during initialization.
- Implemented defensive attribute access using `.get()` in property accessors and dedicated `get_transport_info_value` / `set_transport_info_value` methods.

```python
# Example implementation structure
class TransferRequest:
    def __init__(self, patient_data, location, transport_info=None):
        self.patient_data = patient_data
        self.location = location
        self.transport_info = transport_info or {}
        self._validate_required_fields()
    
    @property
    def clinical_text(self):
        return self.transport_info.get('clinical_text', '')
    
    @clinical_text.setter
    def clinical_text(self, value):
        self.transport_info['clinical_text'] = value
    
    # Similar properties for scoring_results and human_suggestions
    
    def _validate_required_fields(self):
        # Validation logic here
        pass
```

#### Step 2: Implement Serialization Methods
- **Status: Completed**
- `to_dict()` (as `model_dump()`) and `from_dict()` (as `model_validate()`) methods are provided by Pydantic for consistent serialization.
- Nested objects are properly serialized by Pydantic.
- Field validation during deserialization is handled by Pydantic.

#### Step 3: Create Migration Utility
- **Status: Not Started** (This was not part of the completed subtask)
- Develop a migration utility to convert old TransferRequest objects to the new format
- Add logging to track migration successes and failures
- Implement data recovery for potentially corrupted records

#### Testing Strategy: TransferRequest Model
- **Status: Implemented and Passing**
- A comprehensive test suite exists in `tests/core/test_models.py`.
- Unit tests cover each property accessor.
- Serialization and deserialization are implicitly tested by Pydantic model instantiation and usage in tests.
- Tests for backward compatibility (e.g., `sending_facility_location`) are included.
- Helper methods like `get_transport_info_value` and `set_transport_info_value` are tested.

```python
# Example test strategy
def test_clinical_text_property():
    # Test getting and setting clinical_text via property
    request = TransferRequest(patient_data, location)
    request.clinical_text = "Test clinical text"
    assert request.clinical_text == "Test clinical text"
    assert request.transport_info['clinical_text'] == "Test clinical text"

def test_missing_required_fields():
    # Test validation of required fields
    with pytest.raises(ValidationError):
        TransferRequest(patient_data=None, location=location)
```

### Implementation Plan: Recommendation Model

**Status: Completed**

#### Step 1: Enhance Recommendation Class
- **Status: Completed**
- Extended the `Recommendation` class to include all UI-required fields such as `transport_details` (dict), `conditions` (dict), and `explainability_details` (dict with a default factory).
- Implemented `recommended_level_of_care` (str) with inference logic in `infer_recommended_level_of_care` method.

#### Step 2: Implement Validation Methods
- **Status: Completed**
- Validation methods for fields like `confidence_score` and `explainability_details` are implemented using Pydantic validators.
- Fallback values for optional fields are handled by Pydantic's `default` or `default_factory`.
- Data type checking is inherent to Pydantic model definitions.

#### Step 3: Improve Serialization
- **Status: Completed**
- JSON serialization and deserialization are handled by Pydantic's `model_dump()` and `model_validate()`.
- Schema validation is part of Pydantic's core functionality.

#### Testing Strategy: Recommendation Model
- **Status: Implemented and Passing**
- Unit tests in `tests/core/test_models.py` cover new fields, properties, and methods like `validate_confidence_score`, `ensure_explainability_details`, `has_transport_weather_info`, `get_travel_time_estimate`, and `infer_recommended_level_of_care`.
- Serialization/deserialization are implicitly tested.
- Validation for required fields and boundary conditions (e.g., `confidence_score`) are tested.

### Implementation Plan: HospitalCampus Model

**Status: Completed**

#### Step 1: Complete Essential Fields
- **Status: Completed**
- Finalized the `HospitalCampus` class with essential fields: `campus_id` (str), `name` (str), `location` (Location object).
- Validation for required fields is handled by Pydantic.
- Property accessors are not explicitly needed as Pydantic handles attribute access.

#### Step 2: Add Care Levels and Specialties
- **Status: Completed**
- Implemented `care_levels` (List[CareLevel]) and `specialties` (List[Specialty]) as standard fields using Enum types.
- Validation for these fields is handled by Pydantic based on Enum definitions.

#### Step 3: Distance Calculation Methods
- **Status: Completed**
- Implemented Haversine formula for accurate Earth-surface distance calculation in `calculate_distance` method.
- Related methods `calculate_driving_distance_km` and `estimate_driving_time_minutes` are also present.
- Caching was not part of this subtask.

#### Testing Strategy: HospitalCampus Model
- **Status: Implemented and Passing**
- Unit tests in `tests/core/test_models.py` cover properties and methods like `calculate_distance`, `calculate_driving_distance_km`, `estimate_driving_time_minutes`, `has_care_level`, and `has_specialty`.
- Distance calculation is tested with known coordinate pairs.
- Serialization/deserialization are implicitly tested.
- The `BedCensus` instantiation within the test setup was corrected to align with the model definition.

## 2. Core Decision Support & Explainability (Highest Priority)

### Implementation Plan: LLM Reasoning Display

#### Step 1: Design Reasoning Data Structure
- Create a standardized schema for reasoning data
- Define required fields (factors considered, alternatives, decision points)
- Implement serialization/deserialization methods

#### Step 2: Enhance LLM Output Processing
- Modify LLM prompts to generate structured reasoning data
- Update response parsing to extract reasoning components
- Add fallback mechanism for unstructured responses

#### Step 3: Implement UI Components
- Create a `ReasoningDisplay` widget in the recommendation UI
- Implement formatting with visual emphasis on key points
- Add color coding for different recommendation types
- Improve whitespace and organization for better readability

#### Testing Strategy: LLM Reasoning Display
- Create unit tests for reasoning data extraction
- Implement UI component tests with mock data
- Test handling of malformed or incomplete reasoning data
- Create automated visual regression tests for UI components
- Develop a test suite of sample LLM responses with expected extraction results

### Implementation Plan: Scoring System Transparency

#### Step 1: Create Score Breakdown Components
- Develop interactive visualization components for pediatric scores
- Implement expandable sections for score details
- Create tooltips explaining score significance
- Add visual highlighting for critical/concerning scores

#### Step 2: LLM Score Integration
- Modify LLM prompts to explicitly reference scoring systems
- Implement validation to confirm LLM uses scores appropriately
- Add score utilization tracking in decision-making
- Create documentation of score interpretation in LLM context

#### Step 3: Score Visualization Enhancement
- Implement visual indicators for score relationships
- Create comparative views between different scoring systems
- Add historical context for score changes over time

#### Testing Strategy: Scoring System Transparency
- Unit test score calculation and visualization components
- Implement mock LLM responses to test score utilization
- Create validation tests for score interpretation
- Develop automated UI tests for score breakdown components
- Test score visualization with boundary and edge cases

### Implementation Plan: Contextual Information Display

#### Step 1: Input Summary Component
- Create a comprehensive summary view of all request details
- Implement data verification UI before processing
- Add ability to edit/correct input data

#### Step 2: Data Utilization Tracking
- Implement tracking of which data points influenced recommendations
- Create visualization of data importance in decision-making
- Add logging of data utilization patterns

#### Step 3: Exclusion Visualization
- Design clear visualization of applicable exclusions
- Implement "not applicable" indicators for irrelevant exclusions
- Create visual hierarchy of information

#### Testing Strategy: Contextual Information Display
- Unit test all display components
- Create automated tests for data editing functionality
- Test display with various data conditions (missing, complete, invalid)
- Implement visual regression tests for UI components
- Test integration with data model changes

## 3. Map & Visualization Enhancements

### Implementation Plan: Basic Map Integration

#### Step 1: Map Component Implementation
- Select appropriate mapping library (e.g., Folium, Leaflet)
- Create a `MapView` component for the application
- Implement basic map rendering with zoom/pan controls

#### Step 2: Location Visualization
- Add sending location and hospital markers to the map
- Implement tooltip information for each marker
- Create visual highlighting for recommended hospitals

#### Step 3: Geographic Proximity Visualization
- Add distance circles or heat maps to show proximity
- Implement visual comparison of hospital distances
- Create toggleable overlays for different visualization modes

#### Testing Strategy: Map Integration
- Unit test map component initialization and rendering
- Implement automated tests for marker placement accuracy
- Test map interactions with simulated events
- Create visual regression tests for map rendering
- Test boundary conditions (e.g., locations at poles, international date line)

### Implementation Plan: Distance & Travel Integration

#### Step 1: External Map Links
- Implement "Open in External Maps" functionality
- Create URL generation for multiple mapping services
- Add deep linking support where available

#### Step 2: Travel Information Display
- Implement straight-line distance calculation and display
- Add approximate driving time estimation
- Create simple traffic condition indicators
- Implement basic weather alert integration

#### Step 3: Proximity-Based Decision Logic
- Update recommendation algorithm to prioritize proximity
- Implement threshold-based logic for skipping closest facilities
- Create validation for distant facility recommendations

#### Testing Strategy: Distance & Travel Integration
- Unit test distance calculation with known coordinates
- Test URL generation for external mapping services
- Implement mocks for traffic and weather data sources
- Create automated tests for proximity-based decision logic
- Test boundary conditions for distance calculations

### Implementation Plan: Visual Cues for Priority

#### Step 1: Design Visual Indicators
- Create a color coding system for urgency levels
- Design icons for specific care needs
- Implement conditional formatting rules

#### Step 2: Accessibility Implementation
- Ensure all visual cues have text alternatives
- Implement redundant coding (not relying solely on color)
- Add keyboard navigation for interactive elements

#### Step 3: Integration with Scoring Systems
- Link visual cues to scoring system results
- Create dynamic updates based on score changes
- Implement priority visualization based on multiple factors

#### Testing Strategy: Visual Cues
- Unit test all visual indicator components
- Implement accessibility testing with screen readers
- Create visual regression tests for all indicators
- Test integration with scoring system changes
- Verify color contrast meets accessibility standards

## 4. Responsive UI and Workflow Improvements

### Implementation Plan: Asynchronous Operations

#### Step 1: Threading Implementation
- Refactor LLM operations to use a thread pool
- Implement a `BackgroundTaskManager` class
- Add progress tracking for long-running operations

#### Step 2: UI Responsiveness
- Implement non-blocking UI updates during processing
- Add cancellation capability for in-progress operations
- Create responsive feedback mechanisms

#### Step 3: LLM Interaction Logging
- Implement comprehensive logging of LLM interactions
- Add timestamping for all operations
- Create debug message logging for input/output payloads
- Implement log rotation and storage

#### Testing Strategy: Asynchronous Operations
- Unit test threading implementation with mock operations
- Implement stress tests for concurrent operations
- Create automated tests for cancellation functionality
- Test logging system with various message types
- Verify thread safety with race condition tests

```python
# Example test for asynchronous operations
def test_llm_operation_cancellation():
    # Setup a long-running LLM operation
    task_manager = BackgroundTaskManager()
    task_id = task_manager.start_task(mock_llm_call, args=(large_input,))
    
    # Request cancellation
    task_manager.cancel_task(task_id)
    
    # Verify task was cancelled and resources cleaned up
    assert task_manager.get_task_status(task_id) == TaskStatus.CANCELLED
```

### Implementation Plan: "Load Demo Scenario" Feature

#### Step 1: Create Demo Scenarios
- Develop 3-5 diverse patient scenarios
- Implement serialization format for scenarios
- Create documentation for each scenario

#### Step 2: Scenario Loading Mechanism
- Implement one-click loading functionality
- Add progress indicators for scenario loading
- Create error handling for corrupted scenarios

#### Step 3: Scenario Management
- Add ability to save custom scenarios
- Implement scenario export/import
- Create scenario editing capabilities

#### Testing Strategy: Demo Scenarios
- Unit test scenario loading with all predefined scenarios
- Implement integration tests with the full application pipeline
- Test scenario loading with corrupted data
- Create automated tests for scenario management functions
- Verify scenario fidelity across application versions

### Implementation Plan: Streamlined Recommendation Comparison

#### Step 1: Comparison UI Implementation
- Create side-by-side comparison view
- Implement highlighting of key differences
- Add toggling between detailed and summary views

#### Step 2: Sorting and Filtering
- Implement sorting by different criteria
- Add filtering capabilities for recommendation lists
- Create persistent user preferences for sorting/filtering

#### Step 3: Confidence Calculation
- Develop algorithm for legitimate confidence calculation
- Implement data completeness assessment
- Add score certainty and decision path clarity factors
- Remove random number generators and arbitrary fallbacks

#### Testing Strategy: Recommendation Comparison
- Unit test all comparison UI components
- Implement visual regression tests for comparison views
- Test sorting and filtering with various data sets
- Create validation tests for confidence calculation
- Test boundary conditions for all numerical comparisons

### Implementation Plan: Graceful Error Handling

#### Step 1: Error Recovery Mechanisms
- Implement robust fallbacks for LLM failures
- Create graceful degradation paths for all components
- Add appropriate user messaging for error conditions

#### Step 2: Diagnostic Logging
- Implement detailed diagnostic logging for errors
- Create error categorization system
- Add context capture for error conditions

#### Step 3: User Feedback
- Design helpful error messages for end users
- Implement suggested actions for common errors
- Create error reporting mechanism

#### Testing Strategy: Error Handling
- Unit test all error recovery mechanisms
- Implement chaos testing by injecting failures
- Test graceful degradation with various failure scenarios
- Verify appropriate user messaging for all error types
- Create automated tests for recovery from common failures

## 5. Focused Pediatric Scoring Implementation

### Implementation Plan: PEWS (Pediatric Early Warning Score)

#### Step 1: Core Implementation
- Create the `PediatricEarlyWarningScore` class
- Implement respiratory, cardiovascular, and behavior subscores
- Add age-appropriate thresholds
- Implement interpretation guidelines

#### Step 2: Visualization
- Create visual representation of score components
- Implement color coding for score severity
- Add trend visualization for score changes

#### Step 3: Integration
- Connect PEWS calculation to patient data
- Implement automatic scoring from clinical inputs
- Add score-based recommendations

#### Testing Strategy: PEWS
- Unit test score calculation with various input values
- Create test cases for all boundary conditions
- Implement validation with clinical test cases
- Test integration with patient data sources
- Verify visual representation accuracy

```python
# Example test for PEWS calculation
def test_pews_respiratory_subscore():
    # Test calculation of respiratory subscore
    score = PediatricEarlyWarningScore()
    
    # Test normal values
    assert score.calculate_respiratory_subscore(rate=20, effort="normal", oxygen=21) == 0
    
    # Test moderate values
    assert score.calculate_respiratory_subscore(rate=30, effort="mild_increase", oxygen=28) == 1
    
    # Test severe values
    assert score.calculate_respiratory_subscore(rate=50, effort="severe_increase", oxygen=40) == 2
```

### Implementation Plan: TRAP (Transport Risk Assessment in Pediatrics)

#### Step 1: Core Implementation
- Create the `TransportRiskAssessment` class
- Implement risk assessment criteria
- Add transport team requirement determination
- Create reference information for interpretation

#### Step 2: Visualization
- Implement visual indicators for risk levels
- Create transport team requirement display
- Add detailed breakdown of risk factors

#### Step 3: Integration
- Connect TRAP calculation to patient data
- Implement automatic risk assessment
- Add integration with transportation planning

#### Testing Strategy: TRAP
- Unit test risk assessment with various input combinations
- Create test cases for all risk levels
- Implement validation with clinical test cases
- Test integration with transportation planning
- Verify visual representation accuracy

### Implementation Plan: Additional Scoring Systems

#### Step 1: Foundation Architecture
- Create a common interface for all scoring systems
- Implement base classes for score calculation
- Design extensible visualization components

#### Step 2: Basic Implementation
- Create simplified implementations for CAMEO II, PRISM III, Queensland, TPS, and CHEWS
- Implement core calculations for each system
- Add placeholder UI elements

#### Step 3: Documentation
- Create comprehensive documentation for each scoring system
- Implement in-app help for score interpretation
- Add reference information for clinical context

#### Testing Strategy: Additional Scoring Systems
- Unit test base scoring system implementation
- Create test cases for each specific scoring system
- Implement validation with clinical test cases
- Test UI placeholder functionality
- Verify extensibility for future enhancements

## 6. Streamlined LLM Integration

### Implementation Plan: Focused LLM Prompt Engineering

#### Step 1: Prompt Template Optimization
- Refine prompt templates for clarity and structure
- Add explicit instructions for distance/proximity calculations
- Implement specific guidance for hospital comparisons

#### Step 2: Example Integration
- Create a library of high-quality reasoning examples
- Implement example selection based on request similarity
- Add contextual examples for different request types

#### Step 3: Prompt Testing Framework
- Create automated testing for prompt effectiveness
- Implement A/B testing for prompt variations
- Add metrics for prompt performance

#### Testing Strategy: LLM Prompts
- Develop a test suite of sample requests with expected outcomes
- Implement evaluation metrics for response quality
- Create automated tests for prompt template rendering
- Test prompt performance with various input conditions
- Verify prompt reliability across different LLM versions

### Implementation Plan: Robust LLM Response Handling

#### Step 1: Improved JSON Parsing
- Enhance JSON parsing with better error recovery
- Implement schema validation for responses
- Add fallback parsing for malformed responses

#### Step 2: Response Validation
- Create validation rules for required fields
- Implement fallback templates for missing data
- Add logging for validation failures

#### Step 3: Response Structuring
- Create standardized response format matching UI needs
- Implement transformation layer for raw LLM responses
- Add validation for transformed responses

#### Testing Strategy: LLM Response Handling
- Unit test parsing with various response formats
- Create test cases for malformed responses
- Implement validation tests for all required fields
- Test fallback mechanisms with incomplete responses
- Verify transformation accuracy with complex responses

### Implementation Plan: Distance Integration

#### Step 1: Distance Calculation
- Implement Haversine formula for straight-line distance
- Add caching for performance optimization
- Create distance matrix for multiple hospitals

#### Step 2: Proximity Scoring
- Develop proximity scoring algorithm
- Implement weighting based on care level requirements
- Add distance thresholds for different transport modes

#### Step 3: LLM Integration
- Update LLM prompts to emphasize proximity importance
- Add pre-calculated distances to LLM context
- Implement validation for distance-based decisions

#### Testing Strategy: Distance Integration
- Unit test distance calculation with known coordinates
- Create test cases for proximity scoring
- Implement validation for distance-based recommendations
- Test caching performance with large hospital sets
- Verify LLM integration with mock responses

### Implementation Plan: RecommendationHandler Improvements

#### Step 1: Field Extraction Enhancement
- Fix extraction of transport_details and conditions fields
- Implement robust parsing for complex nested structures
- Add validation for extracted fields

#### Step 2: UI Data Population
- Ensure all UI tabs receive proper data
- Implement default values for missing fields
- Add data transformation for UI-specific formats

#### Step 3: Logging and Diagnostics
- Improve logging for troubleshooting
- Add detailed context for extraction failures
- Implement performance metrics for extraction process

#### Testing Strategy: RecommendationHandler
- Unit test field extraction with various response formats
- Create test cases for all UI data requirements
- Implement integration tests with UI components
- Test default value generation for missing fields
- Verify logging effectiveness with simulated failures

## Implementation Sequence and Timeline

### Phase 1: Foundation (Weeks 1-2)
1. **Core Data Model Fixes**
   - TransferRequest Model refactoring
   - Recommendation Model enhancements
   - HospitalCampus Model completion

2. **Core Decision Support: Data Structures**
   - Reasoning data structure design
   - Score breakdown components implementation
   - Input summary component creation

### Phase 2: Core Functionality (Weeks 3-4)
3. **Core Decision Support: Integration**
   - LLM output processing enhancements
   - Score utilization validation
   - Data utilization tracking implementation

4. **Map & Basic Visualization**
   - Basic map component implementation
   - Location visualization
   - External map links functionality

### Phase 3: Enhanced Functionality (Weeks 5-6)
5. **Responsive UI Foundation**
   - Asynchronous operations implementation
   - UI responsiveness improvements
   - Demo scenario feature creation

6. **Map & Advanced Visualization**
   - Geographic proximity visualization
   - Travel information display
   - Visual cues for priority implementation

### Phase 4: Clinical Scoring Systems (Weeks 7-8)
7. **Core Pediatric Scoring**
   - PEWS implementation
   - TRAP implementation
   - Scoring system foundation architecture

8. **Advanced Pediatric Scoring**
   - Additional scoring systems basic implementation
   - Score visualization enhancement
   - Score documentation creation

### Phase 5: LLM Optimization (Weeks 9-10)
9. **LLM Input Improvements**
   - Prompt template optimization
   - Example integration
   - Distance integration with LLM context

10. **LLM Output Handling**
    - JSON parsing enhancements
    - Response validation implementation
    - RecommendationHandler improvements

### Phase 6: Refinement (Weeks 11-12)
11. **Recommendation Comparison**
    - Comparison UI implementation
    - Sorting and filtering functionality
    - Confidence calculation algorithm

12. **Error Handling & Logging**
    - Error recovery mechanisms implementation
    - Diagnostic logging enhancements
    - User feedback improvements

## Progress Tracking and Validation

To ensure quality implementation and enable non-GUI validation, we will implement the following:

### Automated Testing Framework
- Unit tests for all components (target: 90%+ coverage)
- Integration tests for component interactions
- End-to-end tests for critical workflows
- Visual regression tests for UI components

### Continuous Integration Pipeline
- Automated test execution on every commit
- Code quality checks (linting, static analysis)
- Performance benchmarking for critical operations
- Documentation generation from code

### Validation Metrics
- Track model serialization/deserialization success rates
- Measure LLM response quality and parsing success
- Monitor score calculation accuracy
- Track recommendation confidence accuracy

### Monitoring Dashboard
- Create a developer dashboard for implementation progress
- Implement metrics visualization for key components
- Add alerting for regression in critical functionality
- Create historical tracking of performance improvements

This plan ensures each component can be validated independently of the GUI, with comprehensive automated testing and clear progress tracking throughout implementation.

## 1. Core Data Model Fixes (Critical Priority)

### Implementation Plan: TransferRequest Model

#### Step 1: Refactor TransferRequest Class
- Refine the `TransferRequest` class to properly utilize the `transport_info` dictionary for extended data
- Implement proper property accessors for `clinical_text`, `scoring_results`, and `human_suggestions`
- Add validation for required fields during initialization
- Add defensive attribute access with appropriate error handling

```python
# Example implementation structure
class TransferRequest:
    def __init__(self, patient_data, location, transport_info=None):
        self.patient_data = patient_data
        self.location = location
        self.transport_info = transport_info or {}
        self._validate_required_fields()
    
    @property
    def clinical_text(self):
        return self.transport_info.get('clinical_text', '')
    
    @clinical_text.setter
    def clinical_text(self, value):
        self.transport_info['clinical_text'] = value
    
    # Similar properties for scoring_results and human_suggestions
    
    def _validate_required_fields(self):
        # Validation logic here
        pass
```

#### Step 2: Implement Serialization Methods
- Add `to_dict()` and `from_dict()` methods for consistent serialization
- Ensure all nested objects are properly serialized
- Implement field validation during deserialization

#### Step 3: Create Migration Utility
- Develop a migration utility to convert old TransferRequest objects to the new format
- Add logging to track migration successes and failures
- Implement data recovery for potentially corrupted records

#### Testing Strategy: TransferRequest Model
- Create a comprehensive test suite in `tests/models/test_transfer_request.py`
- Implement unit tests for each property accessor
- Test serialization and deserialization with various data conditions
- Add property-based tests using Hypothesis to test boundary conditions
- Create specific tests for backward compatibility with old data formats
- Implement integration tests with dependent components

```python
# Example test strategy
def test_clinical_text_property():
    # Test getting and setting clinical_text via property
    request = TransferRequest(patient_data, location)
    request.clinical_text = "Test clinical text"
    assert request.clinical_text == "Test clinical text"
    assert request.transport_info['clinical_text'] == "Test clinical text"

def test_missing_required_fields():
    # Test validation of required fields
    with pytest.raises(ValidationError):
        TransferRequest(patient_data=None, location=location)
```

### Implementation Plan: Recommendation Model

#### Step 1: Enhance Recommendation Class
- Extend the `Recommendation` class to include all UI-required fields
- Add proper implementations for `transport_details` and `conditions` fields
- Create a structured `explainability_details` field with all reasoning components
- Implement `recommended_level_of_care` with proper inference logic

#### Step 2: Implement Validation Methods
- Add validation methods to ensure all required fields are populated
- Create fallback values for optional fields
- Implement data type checking for all fields
- Add warning logging for missing or invalid data

#### Step 3: Improve Serialization
- Update JSON serialization to handle complex nested fields
- Implement custom JSON encoders/decoders if needed
- Add schema validation for serialized data

#### Testing Strategy: Recommendation Model
- Create unit tests for all new fields and properties
- Implement serialization/deserialization tests with various data conditions
- Test integration with UI components using mock objects
- Create validation tests for all required fields
- Test boundary conditions for all numerical fields

### Implementation Plan: HospitalCampus Model

#### Step 1: Complete Essential Fields
- Finalize the `HospitalCampus` class with all essential fields
- Standardize location representation
- Add validation for required fields
- Implement proper property accessors

#### Step 2: Add Care Levels and Specialties
- Implement standardized representation for care levels
- Add specialty classification with consistent taxonomy
- Create validation for specialty and care level data

#### Step 3: Distance Calculation Methods
- Implement Haversine formula for accurate Earth-surface distance calculation
- Add caching of distance calculations for performance
- Create methods for comparing distances between multiple campuses

#### Testing Strategy: HospitalCampus Model
- Unit test all properties and methods
- Test distance calculation with known coordinate pairs
- Implement serialization/deserialization tests
- Test boundary conditions for all numerical fields
- Create validation tests for all required fields

## 1. Core Decision Support & Explainability

### Implementation Plan: LLM Reasoning Display

#### Step 1: Design Reasoning Data Structure
- Create a standardized schema for reasoning data
- Define required fields (factors considered, alternatives, decision points)
- Implement serialization/deserialization methods

#### Step 2: Enhance LLM Output Processing
- Modify LLM prompts to generate structured reasoning data
- Update response parsing to extract reasoning components
- Add fallback mechanism for unstructured responses

#### Step 3: Implement UI Components
- Create a `ReasoningDisplay` widget in the recommendation UI
- Implement formatting with visual emphasis on key points
- Add color coding for different recommendation types
- Improve whitespace and organization for better readability

#### Testing Strategy: LLM Reasoning Display
- Create unit tests for reasoning data extraction
- Implement UI component tests with mock data
- Test handling of malformed or incomplete reasoning data
- Create automated visual regression tests for UI components
- Develop a test suite of sample LLM responses with expected extraction results

### Implementation Plan: Scoring System Transparency

#### Step 1: Create Score Breakdown Components
- Develop interactive visualization components for pediatric scores
- Implement expandable sections for score details
- Create tooltips explaining score significance
- Add visual highlighting for critical/concerning scores

#### Step 2: LLM Score Integration
- Modify LLM prompts to explicitly reference scoring systems
- Implement validation to confirm LLM uses scores appropriately
- Add score utilization tracking in decision-making
- Create documentation of score interpretation in LLM context

#### Step 3: Score Visualization Enhancement
- Implement visual indicators for score relationships
- Create comparative views between different scoring systems
- Add historical context for score changes over time

#### Testing Strategy: Scoring System Transparency
- Unit test score calculation and visualization components
- Implement mock LLM responses to test score utilization
- Create validation tests for score interpretation
- Develop automated UI tests for score breakdown components
- Test score visualization with boundary and edge cases

### Implementation Plan: Contextual Information Display

#### Step 1: Input Summary Component
- Create a comprehensive summary view of all request details
- Implement data verification UI before processing
- Add ability to edit/correct input data

#### Step 2: Data Utilization Tracking
- Implement tracking of which data points influenced recommendations
- Create visualization of data importance in decision-making
- Add logging of data utilization patterns

#### Step 3: Exclusion Visualization
- Design clear visualization of applicable exclusions
- Implement "not applicable" indicators for irrelevant exclusions
- Create visual hierarchy of information

#### Testing Strategy: Contextual Information Display
- Unit test all display components
- Create automated tests for data editing functionality
- Test display with various data conditions (missing, complete, invalid)
- Implement visual regression tests for UI components
- Test integration with data model changes

## 2. Map & Visualization Enhancements

### Implementation Plan: Basic Map Integration

#### Step 1: Map Component Implementation
- Select appropriate mapping library (e.g., Folium, Leaflet)
- Create a `MapView` component for the application
- Implement basic map rendering with zoom/pan controls

#### Step 2: Location Visualization
- Add sending location and hospital markers to the map
- Implement tooltip information for each marker
- Create visual highlighting for recommended hospitals

#### Step 3: Geographic Proximity Visualization
- Add distance circles or heat maps to show proximity
- Implement visual comparison of hospital distances
- Create toggleable overlays for different visualization modes

#### Testing Strategy: Map Integration
- Unit test map component initialization and rendering
- Implement automated tests for marker placement accuracy
- Test map interactions with simulated events
- Create visual regression tests for map rendering
- Test boundary conditions (e.g., locations at poles, international date line)

### Implementation Plan: Distance & Travel Integration

#### Step 1: External Map Links
- Implement "Open in External Maps" functionality
- Create URL generation for multiple mapping services
- Add deep linking support where available

#### Step 2: Travel Information Display
- Implement straight-line distance calculation and display
- Add approximate driving time estimation
- Create simple traffic condition indicators
- Implement basic weather alert integration

#### Step 3: Proximity-Based Decision Logic
- Update recommendation algorithm to prioritize proximity
- Implement threshold-based logic for skipping closest facilities
- Create validation for distant facility recommendations

#### Testing Strategy: Distance & Travel Integration
- Unit test distance calculation with known coordinates
- Test URL generation for external mapping services
- Implement mocks for traffic and weather data sources
- Create automated tests for proximity-based decision logic
- Test boundary conditions for distance calculations

### Implementation Plan: Visual Cues for Priority

#### Step 1: Design Visual Indicators
- Create a color coding system for urgency levels
- Design icons for specific care needs
- Implement conditional formatting rules

#### Step 2: Accessibility Implementation
- Ensure all visual cues have text alternatives
- Implement redundant coding (not relying solely on color)
- Add keyboard navigation for interactive elements

#### Step 3: Integration with Scoring Systems
- Link visual cues to scoring system results
- Create dynamic updates based on score changes
- Implement priority visualization based on multiple factors

#### Testing Strategy: Visual Cues
- Unit test all visual indicator components
- Implement accessibility testing with screen readers
- Create visual regression tests for all indicators
- Test integration with scoring system changes
- Verify color contrast meets accessibility standards

## 3. Responsive UI and Workflow Improvements

### Implementation Plan: Asynchronous Operations

#### Step 1: Threading Implementation
- Refactor LLM operations to use a thread pool
- Implement a `BackgroundTaskManager` class
- Add progress tracking for long-running operations

#### Step 2: UI Responsiveness
- Implement non-blocking UI updates during processing
- Add cancellation capability for in-progress operations
- Create responsive feedback mechanisms

#### Step 3: LLM Interaction Logging
- Implement comprehensive logging of LLM interactions
- Add timestamping for all operations
- Create debug message logging for input/output payloads
- Implement log rotation and storage

#### Testing Strategy: Asynchronous Operations
- Unit test threading implementation with mock operations
- Implement stress tests for concurrent operations
- Create automated tests for cancellation functionality
- Test logging system with various message types
- Verify thread safety with race condition tests

```python
# Example test for asynchronous operations
def test_llm_operation_cancellation():
    # Setup a long-running LLM operation
    task_manager = BackgroundTaskManager()
    task_id = task_manager.start_task(mock_llm_call, args=(large_input,))
    
    # Request cancellation
    task_manager.cancel_task(task_id)
    
    # Verify task was cancelled and resources cleaned up
    assert task_manager.get_task_status(task_id) == TaskStatus.CANCELLED
```

### Implementation Plan: "Load Demo Scenario" Feature

#### Step 1: Create Demo Scenarios
- Develop 3-5 diverse patient scenarios
- Implement serialization format for scenarios
- Create documentation for each scenario

#### Step 2: Scenario Loading Mechanism
- Implement one-click loading functionality
- Add progress indicators for scenario loading
- Create error handling for corrupted scenarios

#### Step 3: Scenario Management
- Add ability to save custom scenarios
- Implement scenario export/import
- Create scenario editing capabilities

#### Testing Strategy: Demo Scenarios
- Unit test scenario loading with all predefined scenarios
- Implement integration tests with the full application pipeline
- Test scenario loading with corrupted data
- Create automated tests for scenario management functions
- Verify scenario fidelity across application versions

### Implementation Plan: Streamlined Recommendation Comparison

#### Step 1: Comparison UI Implementation
- Create side-by-side comparison view
- Implement highlighting of key differences
- Add toggling between detailed and summary views

#### Step 2: Sorting and Filtering
- Implement sorting by different criteria
- Add filtering capabilities for recommendation lists
- Create persistent user preferences for sorting/filtering

#### Step 3: Confidence Calculation
- Develop algorithm for legitimate confidence calculation
- Implement data completeness assessment
- Add score certainty and decision path clarity factors
- Remove random number generators and arbitrary fallbacks

#### Testing Strategy: Recommendation Comparison
- Unit test all comparison UI components
- Implement visual regression tests for comparison views
- Test sorting and filtering with various data sets
- Create validation tests for confidence calculation
- Test boundary conditions for all numerical comparisons

### Implementation Plan: Graceful Error Handling

#### Step 1: Error Recovery Mechanisms
- Implement robust fallbacks for LLM failures
- Create graceful degradation paths for all components
- Add appropriate user messaging for error conditions

#### Step 2: Diagnostic Logging
- Implement detailed diagnostic logging for errors
- Create error categorization system
- Add context capture for error conditions

#### Step 3: User Feedback
- Design helpful error messages for end users
- Implement suggested actions for common errors
- Create error reporting mechanism

#### Testing Strategy: Error Handling
- Unit test all error recovery mechanisms
- Implement chaos testing by injecting failures
- Test graceful degradation with various failure scenarios
- Verify appropriate user messaging for all error types
- Create automated tests for recovery from common failures

## 4. Focused Pediatric Scoring Implementation

### Implementation Plan: PEWS (Pediatric Early Warning Score)

#### Step 1: Core Implementation
- Create the `PediatricEarlyWarningScore` class
- Implement respiratory, cardiovascular, and behavior subscores
- Add age-appropriate thresholds
- Implement interpretation guidelines

#### Step 2: Visualization
- Create visual representation of score components
- Implement color coding for score severity
- Add trend visualization for score changes

#### Step 3: Integration
- Connect PEWS calculation to patient data
- Implement automatic scoring from clinical inputs
- Add score-based recommendations

#### Testing Strategy: PEWS
- Unit test score calculation with various input values
- Create test cases for all boundary conditions
- Implement validation with clinical test cases
- Test integration with patient data sources
- Verify visual representation accuracy

```python
# Example test for PEWS calculation
def test_pews_respiratory_subscore():
    # Test calculation of respiratory subscore
    score = PediatricEarlyWarningScore()
    
    # Test normal values
    assert score.calculate_respiratory_subscore(rate=20, effort="normal", oxygen=21) == 0
    
    # Test moderate values
    assert score.calculate_respiratory_subscore(rate=30, effort="mild_increase", oxygen=28) == 1
    
    # Test severe values
    assert score.calculate_respiratory_subscore(rate=50, effort="severe_increase", oxygen=40) == 2
```

### Implementation Plan: TRAP (Transport Risk Assessment in Pediatrics)

#### Step 1: Core Implementation
- Create the `TransportRiskAssessment` class
- Implement risk assessment criteria
- Add transport team requirement determination
- Create reference information for interpretation

#### Step 2: Visualization
- Implement visual indicators for risk levels
- Create transport team requirement display
- Add detailed breakdown of risk factors

#### Step 3: Integration
- Connect TRAP calculation to patient data
- Implement automatic risk assessment
- Add integration with transportation planning

#### Testing Strategy: TRAP
- Unit test risk assessment with various input combinations
- Create test cases for all risk levels
- Implement validation with clinical test cases
- Test integration with transportation planning
- Verify visual representation accuracy

### Implementation Plan: Additional Scoring Systems

#### Step 1: Foundation Architecture
- Create a common interface for all scoring systems
- Implement base classes for score calculation
- Design extensible visualization components

#### Step 2: Basic Implementation
- Create simplified implementations for CAMEO II, PRISM III, Queensland, TPS, and CHEWS
- Implement core calculations for each system
- Add placeholder UI elements

#### Step 3: Documentation
- Create comprehensive documentation for each scoring system
- Implement in-app help for score interpretation
- Add reference information for clinical context

#### Testing Strategy: Additional Scoring Systems
- Unit test base scoring system implementation
- Create test cases for each specific scoring system
- Implement validation with clinical test cases
- Test UI placeholder functionality
- Verify extensibility for future enhancements

## 5. Streamlined LLM Integration

### Implementation Plan: Focused LLM Prompt Engineering

#### Step 1: Prompt Template Optimization
- Refine prompt templates for clarity and structure
- Add explicit instructions for distance/proximity calculations
- Implement specific guidance for hospital comparisons

#### Step 2: Example Integration
- Create a library of high-quality reasoning examples
- Implement example selection based on request similarity
- Add contextual examples for different request types

#### Step 3: Prompt Testing Framework
- Create automated testing for prompt effectiveness
- Implement A/B testing for prompt variations
- Add metrics for prompt performance

#### Testing Strategy: LLM Prompts
- Develop a test suite of sample requests with expected outcomes
- Implement evaluation metrics for response quality
- Create automated tests for prompt template rendering
- Test prompt performance with various input conditions
- Verify prompt reliability across different LLM versions

### Implementation Plan: Robust LLM Response Handling

#### Step 1: Improved JSON Parsing
- Enhance JSON parsing with better error recovery
- Implement schema validation for responses
- Add fallback parsing for malformed responses

#### Step 2: Response Validation
- Create validation rules for required fields
- Implement fallback templates for missing data
- Add logging for validation failures

#### Step 3: Response Structuring
- Create standardized response format matching UI needs
- Implement transformation layer for raw LLM responses
- Add validation for transformed responses

#### Testing Strategy: LLM Response Handling
- Unit test parsing with various response formats
- Create test cases for malformed responses
- Implement validation tests for all required fields
- Test fallback mechanisms with incomplete responses
- Verify transformation accuracy with complex responses

### Implementation Plan: Distance Integration

#### Step 1: Distance Calculation
- Implement Haversine formula for straight-line distance
- Add caching for performance optimization
- Create distance matrix for multiple hospitals

#### Step 2: Proximity Scoring
- Develop proximity scoring algorithm
- Implement weighting based on care level requirements
- Add distance thresholds for different transport modes

#### Step 3: LLM Integration
- Update LLM prompts to emphasize proximity importance
- Add pre-calculated distances to LLM context
- Implement validation for distance-based decisions

#### Testing Strategy: Distance Integration
- Unit test distance calculation with known coordinates
- Create test cases for proximity scoring
- Implement validation for distance-based recommendations
- Test caching performance with large hospital sets
- Verify LLM integration with mock responses

### Implementation Plan: RecommendationHandler Improvements

#### Step 1: Field Extraction Enhancement
- Fix extraction of transport_details and conditions fields
- Implement robust parsing for complex nested structures
- Add validation for extracted fields

#### Step 2: UI Data Population
- Ensure all UI tabs receive proper data
- Implement default values for missing fields
- Add data transformation for UI-specific formats

#### Step 3: Logging and Diagnostics
- Improve logging for troubleshooting
- Add detailed context for extraction failures
- Implement performance metrics for extraction process

#### Testing Strategy: RecommendationHandler
- Unit test field extraction with various response formats
- Create test cases for all UI data requirements
- Implement integration tests with UI components
- Test default value generation for missing fields
- Verify logging effectiveness with simulated failures

## Implementation Sequence and Timeline

### Phase 1: Foundation (Weeks 1-2)
1. **Core Data Model Fixes**
   - TransferRequest Model refactoring
   - Recommendation Model enhancements
   - HospitalCampus Model completion

2. **LLM Interaction Logging**
   - Implement comprehensive logging infrastructure
   - Add interaction capture points
   - Create log analysis tools

### Phase 2: Core Functionality (Weeks 3-4)
3. **Pediatric Scoring Implementation**
   - PEWS implementation
   - TRAP implementation
   - Foundation for additional scoring systems

4. **Distance Integration**
   - Distance calculation implementation
   - Proximity scoring development
   - Hospital selection logic updates

### Phase 3: Decision Support (Weeks 5-6)
5. **LLM Integration Improvements**
   - Prompt engineering refinement
   - Response handling enhancements
   - RecommendationHandler improvements

6. **Scoring System Transparency**
   - Score breakdown components
   - LLM score integration
   - Score visualization enhancement

### Phase 4: User Experience (Weeks 7-8)
7. **Map & Visualization**
   - Basic map integration
   - Distance & travel information
   - Visual cues for priority

8. **UI Workflow Improvements**
   - Asynchronous operations
   - Demo scenario feature
   - Recommendation comparison

## Progress Tracking and Validation

To ensure quality implementation and enable non-GUI validation, we will implement the following:

### Automated Testing Framework
- Unit tests for all components (target: 90%+ coverage)
- Integration tests for component interactions
- End-to-end tests for critical workflows
- Visual regression tests for UI components

### Continuous Integration Pipeline
- Automated test execution on every commit
- Code quality checks (linting, static analysis)
- Performance benchmarking for critical operations
- Documentation generation from code

### Validation Metrics
- Track model serialization/deserialization success rates
- Measure LLM response quality and parsing success
- Monitor score calculation accuracy
- Track recommendation confidence accuracy

### Monitoring Dashboard
- Create a developer dashboard for implementation progress
- Implement metrics visualization for key components
- Add alerting for regression in critical functionality
- Create historical tracking of performance improvements

This plan ensures each component can be validated independently of the GUI, with comprehensive automated testing and clear progress tracking throughout implementation.
