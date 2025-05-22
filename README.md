# Pediatric Hospital Transfer Decision Support System

## Overview
This project is a decision support system designed to recommend the most suitable pediatric hospital campus for patient transfer. It focuses on facilities within the Texas Children's Hospital (TCH) network (simulated). The system processes patient data (which can be from unstructured notes), considers hospital exclusion criteria, current bed availability (PICU, NICU, General Peds), travel logistics (road and air, considering weather), and then suggests a campus.

## Features
*   **Pediatric-focused Decision Logic**: Tailored for pediatric patient needs and hospital capabilities.
*   **Patient Data Parsing**: Simulates parsing of patient information from unstructured clinical notes to extract relevant details.
*   **Comprehensive Checks**: Evaluates:
    *   Hospital-specific exclusion criteria.
    *   Real-time bed availability (PICU, NICU, General Pediatric beds).
    *   Travel time via road (using OSRM for realistic routing) and air (helicopter).
    *   Weather conditions impacting air travel.
*   **Actionable Recommendations**: Provides a specific campus recommendation.
*   **Explainability**: Offers insights into the key factors driving a recommendation.
*   **Command-Line Interface (CLI)**: Allows users to interact with the system, input patient data, and receive recommendations.

## Project Structure
```
project-root/
├── data/                 # Sample data files (hospitals, patient notes, weather)
├── src/                  # Source code
│   ├── core/             # Core logic (decision engine, models, exclusion checker)
│   ├── llm/              # LLM text processing (simulated)
│   ├── utils/            # Utility functions (geolocation, travel calculator)
│   ├── explainability/   # Recommendation explainer
│   └── main.py           # CLI application
├── tests/                # Unit tests
├── pyproject.toml        # Project metadata, linter/formatter config
├── requirements.txt      # Project dependencies
└── README.md             # This file
```

## Setup
1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
2.  **Create a Python virtual environment**:
    ```bash
    python -m venv .venv
    ```
3.  **Activate the virtual environment**:
    *   Windows:
        ```bash
        .venv\Scripts\activate
        ```
    *   macOS/Linux:
        ```bash
        source .venv/bin/activate
        ```
4.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *   **Note**: A sufficiently sized environment is needed for dependencies. A previous attempt to install dependencies during testing failed due to an `OSError: [Errno 28] No space left on device`. Ensure adequate disk space.

## Usage (CLI)
The primary way to use the system is via its command-line interface.

*   **Get help on the CLI tool and its commands**:
    ```bash
    python src/main.py recommend --help
    ```

*   **Example Commands**:
    *   **Basic recommendation using a patient notes file**:
        ```bash
        python src/main.py recommend --notes-file data/sample_unstructured_patient_notes.txt --pid "PED_NOTE01" --sfn "Local Clinic Katy" --slat 29.78 --slon -95.77
        ```
        *(This example assumes the first note in `sample_unstructured_patient_notes.txt` is relevant or the CLI might pick one. For specific patient notes, you might need to adapt the notes file or use direct inputs.)*

    *   **Overriding chief complaint and history (patient ID is still recommended for tracking)**:
        ```bash
        python src/main.py recommend --complaint "2yo with high fever and persistent cough" --history "Up to date on immunizations, no known allergies" --pid "PED_CLI01" --sfn "Regional Hospital ER" --slat 30.0 --slon -95.4
        ```

    *   **Using a specific weather data file (ensure patient details are also provided, e.g., via notes or direct flags)**:
        ```bash
        python src/main.py recommend --notes-file data/sample_unstructured_patient_notes.txt --pid "PED_NOTE02" --sfn "Austin North Clinic" --slat 30.45 --slon -97.79 --weather data/sample_weather_conditions.json 
        ```
        *(Note: The CLI currently uses the first weather entry from the JSON file. The patient notes file would need to contain PED_NOTE02 or you'd specify --complaint, etc.)*


## Running Tests
Unit tests are provided to ensure core components function as expected.

*   **Discover and run all tests**:
    ```bash
    python -m unittest discover tests
    ```
*   **Note**: Test execution was recently blocked by an environment disk space error during dependency installation (`OSError: [Errno 28] No space left on device`). Ensure adequate disk space before attempting to install dependencies and run tests.

```
