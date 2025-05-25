# Transfer Center Implementation Checklist

This document provides a prioritized and focused checklist for implementing and enhancing the Transfer Center application, emphasizing decision support, explainability, and user experience.

## 1. Core Decision Support & Explainability (Highest Priority)

- [ ] **LLM Reasoning Display**
  - [ ] Prominently display LLM's reasoning in the recommendation UI
  - [ ] Show key factors considered (distance, specialties, care levels)
  - [ ] Highlight why one hospital was chosen over alternatives
  - [ ] Format reasoning in a clear, readable way with visual emphasis on key points
  - [ ] **[ISSUE-3]** Implement color coding for different recommendation types
  - [ ] **[ISSUE-3]** Improve whitespace and organization for better readability

- [ ] **Scoring System Transparency**
  - [ ] Implement interactive score breakdown for pediatric scores
  - [ ] Show the specific inputs that led to each score (e.g., PEWS components)
  - [ ] Provide tooltips or expandable sections explaining score significance
  - [ ] Visually highlight critical/concerning scores
  - [ ] **[ISSUE-5]** Confirm the LLM is using scores appropriately in decision-making
  - [ ] **[ISSUE-5]** Add validation checks for score utilization
  - [ ] **[ISSUE-5]** Improve documentation of score interpretation in the LLM context

- [ ] **Fix Critical Data Structure Issues**
  - [ ] Ensure transport_info dictionary properly stores clinical_text, scoring_results, and human_suggestions
  - [ ] Fix attribute access in TransferRequest objects
  - [ ] Properly populate all recommendation fields required by UI components
  - [ ] Add validation to prevent missing data errors

- [ ] **Contextual Information Display**
  - [ ] Create clear input summary showing all request details
  - [ ] Allow users to verify data accuracy before processing
  - [ ] Display data used for recommendation generation
  - [ ] Add ability to edit/correct input data if needed
  - [ ] **[ISSUE-3]** Clearly display applicable/non-applicable exclusions
  - [ ] **[ISSUE-3]** Create visual hierarchy of information

## 2. Map & Visualization Enhancements

- [ ] **Basic Map Integration**
  - [ ] Display sending location and recommended hospitals on map
  - [ ] Use simple pins/markers with hospital names
  - [ ] Add zoom and pan controls
  - [ ] Highlight the recommended hospital visually
  - [ ] **[ISSUE-2]** Visualize geographic proximity for decision transparency

- [ ] **Distance & Travel Integration**
  - [ ] Add "Open in External Maps" links for each hospital
  - [ ] Display straight-line distance and approximate driving time
  - [ ] Show simple traffic condition indicators (light/moderate/heavy)
  - [ ] Include basic weather alerts if relevant
  - [ ] **[ISSUE-2]** Make proximity a crucial factor in campus selection
  - [ ] **[ISSUE-2]** Reduce frequency of skipping closest campus
  - [ ] **[ISSUE-2]** Only recommend distant facilities when there's a hard exclusion or no bed availability
  - [ ] **[ISSUE-3]** Add sections for weather and traffic information

- [ ] **Visual Cues for Priority**
  - [ ] Use color coding for urgency based on scoring systems
  - [ ] Add icons to highlight specific care needs
  - [ ] Implement conditional formatting for critical factors
  - [ ] Ensure accessibility (not relying solely on color)

## 3. Responsive UI and Workflow Improvements

- [ ] **Asynchronous Operations**
  - [ ] Implement non-blocking LLM operations using threading
  - [ ] Add progress indicators for long-running operations
  - [ ] Ensure UI remains responsive during processing
  - [ ] Implement cancellation capability for in-progress operations
  - [ ] **[ISSUE-1]** Log every interaction to/from the LLM with timestamps
  - [ ] **[ISSUE-1]** Include debug messages showing input/output payloads
  - [ ] **[ISSUE-1]** Store logs in date-time stamped files for easy retrieval

- [ ] **"Load Demo Scenario" Feature**
  - [ ] Create 3-5 pre-defined patient scenarios for demonstrations
  - [ ] Include diverse cases showcasing different scoring systems
  - [ ] Add one-click loading of complete scenarios
  - [ ] Ensure scenarios demonstrate various recommendation types

- [ ] **Streamlined Recommendation Comparison**
  - [ ] Implement side-by-side comparison of top recommendations
  - [ ] Highlight key differences between options
  - [ ] Allow toggling between detailed and summary views
  - [ ] Add sorting by different criteria (distance, care level, etc.)
  - [ ] **[ISSUE-4]** Develop algorithm for legitimate confidence calculation
  - [ ] **[ISSUE-4]** Consider data completeness, score certainty, and decision path clarity in confidence
  - [ ] **[ISSUE-4]** Remove random number generators and arbitrary fallback values
  - [ ] **[ISSUE-1]** Enable tracing of decision processes

- [ ] **Graceful Error Handling**
  - [ ] Implement robust fallbacks for LLM failures
  - [ ] Show appropriate "Data not available" messages instead of errors
  - [ ] Provide helpful context for resolving issues
  - [ ] Log detailed diagnostics while showing simplified user messages

## 4. Focused Pediatric Scoring Implementation

- [ ] **PEWS (Pediatric Early Warning Score)** - *Priority Implementation*
  - [ ] Implement respiratory, cardiovascular, and behavior subscores
  - [ ] Add clear visual representation of the score components
  - [ ] Include interpretation guidelines and recommended actions
  - [ ] Ensure age-appropriate thresholds

- [ ] **TRAP (Transport Risk Assessment in Pediatrics)** - *Priority Implementation*
  - [ ] Implement core risk assessment criteria
  - [ ] Add visual indicators for transport team requirements
  - [ ] Include reference information for score interpretation

- [ ] **Support for Additional Scoring Systems** (Simplified Initial Implementation)
  - [ ] Create foundation for CAMEO II, PRISM III, Queensland, TPS, and CHEWS
  - [ ] Implement basic score calculation for each system
  - [ ] Add placeholder UI elements with "Coming Soon" indicators where appropriate
  - [ ] Focus on integration architecture rather than full implementation

## 5. Streamlined LLM Integration

- [ ] **Focused LLM Prompt Engineering**
  - [ ] Create clear, structured prompts that directly request needed information
  - [ ] Explicitly request distance/proximity calculations in prompts
  - [ ] Add specific instructions for handling hospital comparisons
  - [ ] Include examples of high-quality reasoning in system prompts

- [ ] **Robust LLM Response Handling**
  - [ ] Improve JSON parsing with better error recovery
  - [ ] Implement fallback templates for missing fields
  - [ ] Add validation to ensure required fields are present
  - [ ] Create structured response format that matches UI needs

- [ ] **Distance Integration**
  - [ ] Implement simple straight-line distance calculation
  - [ ] Add proximity scoring for hospital recommendations
  - [ ] Pre-calculate distances to avoid real-time computation where possible
  - [ ] Use distances as a key factor in LLM decision making
  - [ ] **[ISSUE-2]** Prevent excessive PICU recommendations when not necessary
  - [ ] **[ISSUE-2]** Ensure local distribution of patient care where appropriate

- [ ] **RecommendationHandler Improvements**
  - [ ] Fix extraction of transport_details and conditions fields
  - [ ] Ensure all UI tabs receive proper data
  - [ ] Add default values for missing fields
  - [ ] Improve logging for troubleshooting

## 6. Core Data Model Fixes (Critical)

- [x] **TransferRequest Model**
  - [x] Fix transport_info dictionary usage for extended data
  - [x] Ensure clinical_text, scoring_results, and human_suggestions are properly stored
  - [x] Add validation for required fields (Pydantic handles this)
  - [x] Implement defensive attribute access

- [x] **Recommendation Model**
  - [x] Ensure all UI-required fields are defined and populated
  - [x] Properly implement transport_details and conditions fields
  - [x] Add explainability_details with all reasoning components
  - [x] Include recommended_level_of_care with proper inference

- [x] **HospitalCampus Model**
  - [x] Complete essential fields (campus_id, name, location)
  - [x] Add care_levels and specialties as standard fields
  - [x] Implement simple distance calculation methods (Haversine formula)
  - [x] Ensure proper serialization/deserialization (Pydantic handles this)

## 7. De-Prioritized Features (Future Enhancements)

- [ ] **Advanced Census Data**
  - Simplified for initial implementation: Use static/mock data
  - Future: Real-time bed availability tracking and notifications

- [ ] **Extensive Hospital Management**
  - Simplified for initial implementation: Basic loading and display
  - Future: Full CRUD operations and admin interface

- [ ] **Complete Scoring System Suite**
  - Simplified for initial implementation: Focus on PEWS and TRAP
  - Future: Complete implementation of all seven scoring systems

- [ ] **Advanced Analytics**
  - Simplified for initial implementation: Basic transfer request history
  - Future: Comprehensive reporting and trend analysis

- [ ] **Complex Traffic/Weather Integration**
  - Simplified for initial implementation: Basic text indicators
  - Future: Real-time API integration and detailed visualization

## 8. Implementation Strategy

1. **Fix Critical Issues First**
   - Address attribute access problems in TransferRequest
   - Fix recommendation field population for UI tabs
   - Implement proper transport_info dictionary usage

2. **Build Core Decision Support**
   - Enhance LLM reasoning display
   - Implement scoring system visualization
   - Add hospital comparison features

3. **Add Visual Enhancements**
   - Implement basic map integration
   - Add visual cues for priority
   - Create intuitive UI for recommendation review

4. **Create Demo Scenarios**
   - Develop pre-loaded cases for demonstrations
   - Ensure robust operation with test data
   - Add graceful error handling

5. **Documentation and Polish**
   - Create essential user documentation
   - Add tooltips and help features
   - Implement final UI improvements

This checklist will be updated as implementation progresses and new requirements are identified.
