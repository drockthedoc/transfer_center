# Automated NER Evaluation System for Clinical Text

## 1. Overview

This project provides a set of Python scripts to implement an "automated-assist" evaluation system for Named Entity Recognition (NER) tools, with a focus on their application to clinical text. The system compares NER model outputs against a lexicon derived from a predefined set of clinical exclusion criteria.

The system helps assess how well different NER models (initially focusing on the spaCy/scispaCy ecosystem, but extensible to others) can extract clinically relevant entities from patient vignettes.

The system consists of three main components:
1.  **Lexicon Generator (`lexicon_generator.py`):** Parses a JSON file of clinical exclusion criteria to generate a "Critical Terms & Patterns" Lexicon.
2.  **NER Processor (`ner_processor.py`):** Processes patient vignettes using specified NER models/tools and stores the extracted named entities.
3.  **Evaluator & Reporter (`evaluator.py`):** Compares extracted entities against the lexicon, calculates relevant metrics, and reports the findings.

## 2. Directory Structure

-   `automated_assist_eval/`: Root directory for this evaluation system.
    -   `lexicon_generator.py`: Script to generate the critical lexicon.
    -   `ner_processor.py`: Script to run NER tools on vignettes.
    -   `evaluator.py`: Script to evaluate NER outputs against the lexicon.
    -   `README.md`: This file.
    -   `requirements.txt`: Python dependencies.
    -   `ner_handlers/`: Directory containing NER tool handler implementations.
        -   `base_handler.py`: Abstract base class for all NER handlers.
        -   `spacy_handler.py`: Handler for spaCy models.
        -   `medcat_handler.py`, `cliner_handler.py`, etc.: Stubs/implementations for other NER tools.
    -   `data/`: Contains input data.
        -   `criteria.json`: Sample input clinical criteria JSON (copied from repository's `data/exclusion_criteria_clean.json`).
        -   `vignettes.txt`: Sample patient vignettes (copied from `data/sample_unstructured_patient_notes.txt`).
    -   `output/`: Default directory for generated files.
        -   `critical_lexicon.json`: Output from `lexicon_generator.py`.
        -   `ner_outputs.json`: Output from `ner_processor.py`.

## 3. Setup Instructions

### 3.1. Python Environment

-   Python 3.8 or higher is recommended.
-   It's highly recommended to use a virtual environment:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

### 3.2. Install Dependencies

1.  Install core dependencies from `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
    This will install `spacy`.

### 3.3. Install spaCy Models (Example: scispaCy)

The `SpacyHandler` can load any spaCy-compatible model. For clinical text, `scispaCy` models are recommended.

-   **Example: Install `en_core_sci_sm` (a small scispaCy model):**
    ```bash
    pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_sm-0.5.3.tar.gz
    ```
-   **Example: Install `en_core_sci_md` (a medium scispaCy model):**
    ```bash
    pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_md-0.5.3.tar.gz
    ```
    (Check the [scispaCy GitHub page](https://github.com/allenai/scispacy) for the latest model URLs and versions.)

### 3.4. Dependencies for Other NER Tools (Optional)

The system is designed to be extensible to other NER tools via handlers in the `ner_handlers/` directory. If you wish to fully implement and use handlers for tools like MedCAT, CliNER, Spark NLP, HunFlair, etc., you will need to install them manually according to their own documentation.
The `requirements.txt` file contains commented-out examples. You would typically:
1.  Install the Python package for the tool (e.g., `pip install medcat`).
2.  Download any required models for that tool.
3.  Implement the corresponding handler in the `ner_handlers/` directory if not already complete.

## 4. Running the Scripts

Ensure your virtual environment is activated. All scripts should be run from the `automated_assist_eval/` directory.

### 4.1. `lexicon_generator.py`

Generates the `critical_lexicon.json` from the input criteria.

```bash
python lexicon_generator.py --input_json data/criteria.json --output_lexicon output/critical_lexicon.json
```
-   `--input_json`: Path to the clinical criteria JSON file. (Default: `data/criteria.json`)
-   `--output_lexicon`: Path to save the generated lexicon. (Default: `output/critical_lexicon.json`)
-   `--use_stop_words`: (Optional) Add this flag to enable stop word removal during keyword and key phrase extraction.

### 4.2. `ner_processor.py`

Processes vignettes using specified NER tools and models.

```bash
python ner_processor.py \
    --vignettes_file data/vignettes.txt \
    --output_json output/ner_outputs.json \
    --ner_config ner_config.json
```
Or using a JSON string for config:
```bash
python ner_processor.py \
    --vignettes_file data/vignettes.txt \
    --output_json output/ner_outputs.json \
    --ner_config '[{"tool_type": "spacy", "model_name": "en_core_sci_sm"}]'
```

-   `--vignettes_file`: Path to the text file containing patient vignettes. (Default: `data/vignettes.txt`)
-   `--output_json`: Path to save the extracted NER entities. (Default: `output/ner_outputs.json`)
-   `--ner_config`: (Required) JSON string or path to a JSON file describing the NER tools/models.
    -   **Structure:** A list of objects, each object defining a tool configuration.
    -   **Required keys per object:**
        -   `"tool_type"`: Name of the handler to use (e.g., `"spacy"`, `"medcat"`). Corresponds to the handler filename prefix (e.g., `spacy_handler.py`).
        -   `"model_name"` or `"model_path"` or `"model_path_or_name"`: The model identifier for the tool (e.g., spaCy model name like `"en_core_sci_sm"`, or path to a MedCAT model pack). The `BaseNerHandler` constructor expects `model_path_or_name`. The `ner_processor.py` will use the first available of these keys from the config.

    -   **Example `ner_config.json` file:**
        ```json
        [
          {
            "tool_type": "spacy",
            "model_path_or_name": "en_core_sci_sm"
          },
          {
            "tool_type": "spacy",
            "model_path_or_name": "en_core_sci_md"
          }
          // Add configurations for other tools/models here
          // e.g., { "tool_type": "medcat", "model_path_or_name": "/path/to/your/medcat_model_pack" }
        ]
        ```
        *(Ensure the specified models are installed and accessible in your environment.)*

### 4.3. `evaluator.py`

Evaluates the NER outputs against the lexicon.

```bash
python evaluator.py \
    --lexicon_file output/critical_lexicon.json \
    --ner_outputs_file output/ner_outputs.json \
    --vignettes_file data/vignettes.txt
```
-   `--lexicon_file`: Path to the generated critical lexicon. (Default: `output/critical_lexicon.json`)
-   `--ner_outputs_file`: Path to the NER outputs from `ner_processor.py`. (Default: `output/ner_outputs.json`)
-   `--vignettes_file`: Path to the original vignettes text file (required for coverage analysis). (Default: `data/vignettes.txt`)

The evaluation report is printed to the console.

## 5. Input File Formats

### 5.1. Criteria JSON (`data/criteria.json`)
-   A JSON file containing clinical exclusion criteria.
-   The `lexicon_generator.py` script is designed to traverse this JSON and extract textual strings from lists associated with keys like `"exclusions"`, `"general_exclusions"`, `"ac_exclusion_picu_accept"`, `"accept"`, `"clinical_team_decision"`, and `"notes"` found within nested objects.
-   The structure is based on the provided `data/exclusion_criteria_clean.json` from the parent project.

### 5.2. Vignettes Text File (`data/vignettes.txt`)
-   A plain text file where each patient vignette is typically separated by a line starting with `"Patient #X"` (e.g., "Patient #1: ...").
-   If this pattern is not found, the scripts will attempt to split vignettes by double blank lines.
-   If no delimiters are found, the entire file content might be treated as a single vignette.
-   The vignette identifiers in `ner_outputs.json` and used by `evaluator.py` are derived from these "Patient #X" prefixes or generated sequentially (e.g., "Vignette_1").

## 6. Output File Formats

### 6.1. `critical_lexicon.json`
A JSON file structured as follows:
```json
{
  "keywords": ["term1", "term2", ...],
  "key_phrases": ["key phrase 1", "key phrase 2", ...],
  "numerical_patterns": [
    {
      "text": "<original matched text, e.g., '>=6'>",
      "type": "<'comparison'|'range'|'frequency'|'measurement'>",
      "operator": "<e.g., '>=' (for comparison)>",
      "value": "<numeric value (for comparison/measurement)>",
      "values": "[<num1>, <num2>] (for range)",
      "unit": "<e.g., 'kg', 'days' (optional)>",
      "pattern": "<e.g., 'q1-2' (for frequency)>",
      "original_criterion_context": "<full original criterion string>"
    },
    ...
  ]
}
```

### 6.2. `ner_outputs.json`
A JSON file mapping each NER tool/model configuration to the entities it extracted from each vignette:
```json
{
  "<tool_type>_<model_specifier>": { // e.g., "spacy_en_core_sci_sm"
    "<vignette_id_1>": [ // e.g., "Pt_1_ID_P001_v0"
      {
        "text": "<extracted entity text>",
        "label": "<entity_label>",
        "start_char": <start_character_offset_in_vignette>,
        "end_char": <end_character_offset_in_vignette>
      },
      ... // other entities for this vignette
    ],
    "<vignette_id_2>": [ ... ],
    ...
  },
  "<another_tool_type>_<model_specifier>": { ... },
  ...
}
```

### 6.3. Evaluator Console Output
The `evaluator.py` script prints a report to the console for each NER model/configuration, including:
-   Total vignettes processed.
-   Counts of direct matches for keywords, key phrases, and numerical patterns.
-   Lexicon term coverage percentage.
-   Frequently missed lexicon terms.
-   Common NER labels assigned to matched lexicon terms.

## 7. Extensibility: Adding New NER Tool Handlers

To add support for a new NER tool:
1.  **Create a Handler File:** Add a new Python file in the `automated_assist_eval/ner_handlers/` directory (e.g., `my_tool_handler.py`).
2.  **Implement the Handler Class:**
    -   Import `BaseNerHandler` from `ner_handlers.base_handler`.
    -   Create a class that inherits from `BaseNerHandler` (e.g., `class MyToolHandler(BaseNerHandler):`).
    -   Implement the `load_model(self)` method:
        -   This method should load your NER tool's model using `self.model_path_or_name` (which comes from the `--ner_config`).
        -   Store the loaded model in `self.model`.
        -   Handle any errors during model loading. If loading fails, ensure `self.model` is `None`.
    -   Implement the `process(self, text, vignette_id="unknown")` method:
        -   This method takes the vignette text and should return a list of entities in the standardized format:
            `{"text": str, "label": str, "start_char": int, "end_char": int}`
    -   Optionally, override `get_tool_name(self)` if you want a specific name used in the output keys (default is derived from class name).
3.  **Install Dependencies:** Ensure any Python packages required by your new handler are installed in the environment. Add them to `requirements.txt` if they are general-purpose.
4.  **Update NER Configuration:** Add a new configuration object to your `ner_config.json` (or JSON string) specifying the `"tool_type"` (which should match the prefix of your handler filename, e.g., `"my_tool"`) and the appropriate `"model_path_or_name"`.

Refer to `spacy_handler.py` for an example implementation.
