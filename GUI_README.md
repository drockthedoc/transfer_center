# Texas Children's Hospital Transfer Center GUI

## Overview

This state-of-the-art PyQt-based GUI application enhances the Transfer Center project by providing:

1. **Clinical Data Input** - Paste or enter patient data with an intuitive interface
2. **Human Suggestions** - Add clinical judgment such as "may need ICU" or location preferences
3. **Transport Management** - Specify transport mode (POV, local EMS, or Kangaroo Crew)
4. **ETA Integration** - Account for expected arrival time and traffic patterns
5. **LLM Classification** - Direct integration with medical LLMs via LM Studio
6. **Comprehensive Results** - Detailed recommendations, explanations, and transport analysis

## Getting Started

### Installation

First, install the required dependencies:

```bash
pip install -r requirements.txt
```

### Running the GUI

Launch the application with:

```bash
python gui_main.py
```

## Features

### Clinical Data Input

Enter patient information and clinical data. The system will process this information using both rule-based logic and LLM classification to determine the most appropriate campus for transfer.

### Human Suggestions

Clinicians can provide suggestions that influence the recommendation:

- **Care Level Suggestions** - Indicate if the patient may need ICU, PICU, or NICU care
- **Location Preferences** - Specify if the patient/family prefers Houston or Austin
- **Additional Notes** - Enter any other relevant information

### Transport Options

Specify transportation details that affect recommendations:

- **POV (Private Vehicle)** - Patient arriving via personal transportation
- **Local EMS** - Patient being transported by a local ambulance service
- **Kangaroo Crew** - TCH's specialized transport team with options for:
  - Ground transport
  - Helicopter (rotor-wing)
  - Fixed-wing aircraft

### ETA Specification

You can specify an estimated time of arrival, which will factor in:

- Traffic patterns based on time of day
- Congestion in different metro areas (Houston vs. Austin)
- Travel time impacts on the recommendation

### LLM Integration via LM Studio

The system uses local LLMs through [LM Studio](https://lmstudio.ai/) for text processing and classification:

#### Setting Up LM Studio

1. Download and install [LM Studio](https://lmstudio.ai/)
2. Launch LM Studio and download a recommended medical model:
   - **BioMistral-7B** (recommended for medical classification)
   - **Llama-3-8B-Instruct** (good general performance)
   - **Medusa-14b-v1.0** (medical-specialized)
3. In LM Studio, click "Local Server" in the sidebar
4. Click "Start Server" - this will start a local API server (default: http://localhost:1234/v1)
5. In the Transfer Center GUI, enter this URL in the LLM Configuration section
6. Select your model from the dropdown (must match exactly what's in LM Studio)
7. Click "Test LLM Connection" to verify

## Using the Application

1. **Enter Patient Information**
   - Provide patient ID and clinical data
   - Add any human suggestions that might influence the recommendation

2. **Specify Transport Details**
   - Select transport type
   - For Kangaroo Crew, select transport mode (ground, helicopter, fixed-wing)
   - Enter sending facility information and coordinates

3. **Generate Recommendation**
   - Click "Generate Recommendation"
   - View results across the different tabs:
     - **Recommendation** - Primary campus recommendation with confidence
     - **Explanation** - Detailed explanation of factors that influenced the decision
     - **LLM Classification** - Results from the LLM text processing
     - **Transport Analysis** - Detailed transport time analysis

## Kangaroo Crew Special Features

The application accounts for Kangaroo Crew's unique operational aspects:

- **Houston-based operations** focusing on PICU/NICU transports
- **Austin-based operations** handling EC-EC and acute care bed calls
- **Transport mode differences** including crew preparation time, logistics, and speed
- **Cross-metro considerations** for transfers between Houston and Austin

## Advanced LLM Scaffolding

The LLM integration is built to:

1. Connect to LM Studio's OpenAI-compatible API
2. Process clinical text to extract structured information
3. Identify key medical conditions, vital signs, and care needs
4. Incorporate human suggestions into the classification process
5. Return results in a structured format for the decision engine

### Recommended Models

For optimal medical classification performance:

1. **BioMistral-7B** - Specialized medical knowledge with modest resource requirements
2. **Medusa-14b-v1.0** - Enhanced medical understanding (requires more GPU memory)
3. **Mixtral-8x7B-Instruct-v0.1** - Strong general performance with good medical knowledge

## Transport Time Estimation

The application includes sophisticated transport time estimation accounting for:

- **Traffic patterns** based on time of day and metro area
- **Kangaroo Crew logistics** including prep time and crew dispatch
- **Different transport modes** with realistic speed assumptions
- **Cross-metro operations** with additional time factors
