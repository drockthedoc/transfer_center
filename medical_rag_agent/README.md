# Medical RAG + Agent System

## Quick Start & Setup Verification

### Prerequisites
- Python 3.8+ (tested with Python 3.13)
- Virtual environment recommended

### Setup Verification
Before using the system, run the setup verification script:
```bash
cd medical_rag_agent
python setup_check.py
```

This will check:
- Python version compatibility
- Required dependencies
- Basic module imports
- Package structure integrity

### Installation
If dependencies are missing:
```bash
pip install -r requirements.txt
```

For detailed setup information and troubleshooting, see [FIXES_SUMMARY.md](FIXES_SUMMARY.md).

## Overview

This project implements a Retrieval Augmented Generation (RAG) system combined with an intelligent agent designed for medical decision support, particularly in the context of patient transfers. It leverages local, open-source language models (LLMs) and vector databases to provide healthcare professionals with quick access to relevant information from medical documents and simulated real-time contextual data.

The system can:
1.  Ingest and process PDF medical documents (e.g., textbooks, clinical guidelines, research papers).
2.  Create a searchable vector index of this information.
3.  Utilize an LLM-powered agent with tools to:
    *   Query the medical knowledge base.
    *   Access simulated real-time geographic information (traffic, travel times).
    *   Check simulated medical facility capabilities and status.
4.  Provide synthesized information to aid in complex scenarios like inter-hospital patient transfers.

## Architecture

The system consists of the following main components:

1.  **Document Processor (`src/document_processor.py`):**
    *   Loads PDF documents from a specified folder.
    *   Chunks documents into manageable nodes, prioritizing semantic meaning by attempting to split based on common medical/scientific section headers (e.g., "Introduction", "Methods", "Diagnosis", "Treatment Plan"). If sections are too large or no headers are found, it falls back to sentence-based splitting.
    *   Attaches metadata to each node, including file name and inferred section.

2.  **Indexing Pipeline (`src/indexing.py`):**
    *   Uses a Hugging Face sentence transformer model (e.g., `sentence-transformers/all-MiniLM-L6-v2`) to generate embeddings for the text nodes.
    *   Builds a FAISS vector index from these embeddings.
    *   Persists the FAISS index and associated LlamaIndex storage components (docstore, index_store) to disk.
    *   Provides functionality to load the persisted index.

3.  **Query Engine (`src/query_engine.py`):**
    *   Loads the persisted FAISS index.
    *   Configures a LlamaIndex query engine that can retrieve relevant nodes from the index based on a user query.
    *   Supports filtering queries based on metadata (e.g., searching only within "Treatment Plan" sections).
    *   Can optionally connect to a local LLM (via an OpenAI-compatible API like LM Studio) to synthesize responses based on retrieved context.

4.  **LLM Services (`src/llm_services.py`):**
    *   Provides a standardized way to initialize a LangChain `ChatOpenAI` LLM instance, configured to connect to a local OpenAI-compatible server.
    *   Manages LLM parameters (model name, temperature, API endpoint) via environment variables (`.env` file) and optional runtime configuration.

5.  **Agent Tools (`src/agent/tools.py`):**
    *   Defines LangChain `Tool` objects that the agent can use:
        *   `MedicalInformationRetriever`: Queries the RAG system (built using the query engine).
        *   `GeographicContextTool` (Mock): Simulates providing geographic information.
        *   `FacilityCapabilitiesTool` (Mock): Simulates providing facility status.

6.  **Agent Prompts (`src/agent/prompts.py`):**
    *   `MEDICAL_AGENT_SYSTEM_PROMPT`: Defines the agent's persona, capabilities, and instructions on how to use tools and interact.
    *   `PATIENT_TRANSFER_TASK_PROMPT_TEMPLATE`: A specific prompt template for guiding the agent through a patient transfer decision task (though not fully implemented as a structured output parser in the current agent).

7.  **Medical Agent (`src/agent/agent.py`):**
    *   Initializes the LLM and the defined tools.
    *   Uses LangChain's `create_openai_tools_agent` to create an agent that can reason about when to use the available tools based on the user query and system prompt.
    *   Employs an `AgentExecutor` to run the agent and manage interactions.

8.  **Scripts:**
    *   `scripts/build_index.py`: CLI script to build/rebuild the vector index from source documents.
    *   `scripts/run_agent_cli.py`: CLI application for interacting with the medical agent.
    *   Utility scripts in `scripts/` for creating dummy data or testing components.

9.  **Notebooks:**
    *   `notebooks/1_Document_Ingestion_and_Indexing.ipynb`: Demonstrates the document loading, chunking, embedding, and indexing pipeline.
    *   (Future notebooks could cover agent testing, specific RAG strategies, etc.)

## Features

*   **Local First:** Designed to run with locally hosted LLMs (e.g., via LM Studio, Ollama) and local vector stores.
*   **Open-Source Focused:** Utilizes open-source libraries like LlamaIndex, LangChain, FAISS, and Hugging Face Transformers.
*   **Modular Design:** Components are separated into modules for document processing, indexing, querying, LLM interaction, and agent logic.
*   **Section-Aware Chunking:** Improves context relevance by trying to chunk documents based on common medical section headers.
*   **Metadata Filtering:** Allows queries to be filtered by metadata (e.g., document section) for more precise information retrieval.
*   **Extensible Agent Framework:** The LangChain agent can be extended with more tools and capabilities.
*   **CLI for Indexing and Interaction:** Provides scripts for building the knowledge base and interacting with the agent.

## Project Structure

```
medical_rag_agent/
├── .env                  # Environment variables (API keys, model names, paths)
├── data/                 # Data storage
│   ├── dummy_document.pdf  # Sample PDF for initial tests
│   └── sample_medical_pdfs/ # Folder for PDFs to be indexed by the build_index script
│       └── dummy_document.pdf # Copied here for notebook/script consistency
├── notebooks/            # Jupyter notebooks for experimentation and demos
│   └── 1_Document_Ingestion_and_Indexing.ipynb
├── requirements.txt      # Python dependencies
├── scripts/              # Utility and application scripts
│   ├── build_index.py        # CLI to build the vector index
│   ├── run_agent_cli.py      # CLI to interact with the medical agent
│   ├── create_dummy_pdf.py   # Helper to create a simple PDF
│   └── test_pdf_parser.py    # Helper to test PDF text extraction
├── src/                  # Source code
│   ├── agent/              # Agent-specific logic
│   │   ├── __init__.py
│   │   ├── agent.py          # Core agent setup
│   │   ├── prompts.py        # Agent and task prompts
│   │   └── tools.py          # Agent tools definition
│   ├── __init__.py
│   ├── document_processor.py # PDF loading and chunking logic
│   ├── indexing.py           # Vector index building and loading
│   ├── llm_services.py       # LLM initialization
│   └── query_engine.py       # RAG query engine setup
├── tests/                # Unit and integration tests (currently contains .gitkeep)
│   └── .gitkeep
├── vector_store_notebook/ # Default output for index built by the notebook
│   ├── vector_store.faiss
│   └── ... (other LlamaIndex storage files)
├── vector_store_prod/    # Default output for index built by build_index.py script
│   ├── vector_store.faiss
│   └── ...
└── README.md             # This file
```

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd medical_rag_agent
    ```

2.  **Create a Python Virtual Environment:**
    Recommended to avoid conflicts with other Python projects.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *   **Note on PyTorch (`torch`):** The `requirements.txt` lists `torch`. You need to install the version appropriate for your hardware (CPU or GPU). If you have a compatible NVIDIA GPU and want GPU support:
        *   Visit [PyTorch Get Started](https://pytorch.org/get-started/locally/) to find the correct command for your CUDA version.
        *   For CPU-only (as used in some setup steps for simplicity):
            ```bash
            pip install torch --index-url https://download.pytorch.org/whl/cpu
            pip install torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu # If needed by other parts
            ```
    *   **Note on FAISS:** `faiss-cpu` is listed for CPU-based indexing. If you have a GPU and want to use GPU-accelerated FAISS, you would install `faiss-gpu` (requires CUDA).

4.  **Set up Local LLM Server (e.g., LM Studio):**
    *   Download and install LM Studio ([https://lmstudio.ai/](https://lmstudio.ai/)).
    *   Download a compatible LLM within LM Studio (e.g., a GGUF model like Mistral, Llama, or a specialized medical model if available). Search for models compatible with OpenAI API endpoints.
    *   Start the local server in LM Studio:
        *   Go to the "Local Server" tab (often `localhost:1234`).
        *   Select your downloaded model.
        *   Click "Start Server".
        *   The server should now be running, typically at `http://localhost:1234/v1`.

5.  **Configure Environment Variables:**
    *   Create a `.env` file in the project root (`medical_rag_agent/.env`) by copying the example or creating a new one.
    *   Update the `.env` file with your local LLM server details:
        ```dotenv
        OPENAI_API_BASE="http://localhost:1234/v1"
        OPENAI_API_KEY="not-needed" # Or your actual key if your server requires one
        LOCAL_MODEL_NAME="<your-model-identifier>" # e.g., "mistralai/Mistral-7B-Instruct-v0.1" or as shown in LM Studio
        
        # Optional LLM parameters (defaults are set in llm_services.py if not present)
        # LLM_TEMPERATURE=0.1
        # LLM_MAX_TOKENS=1024
        # LLM_REQUEST_TIMEOUT=120 
        ```
    *   Replace `<your-model-identifier>` with the actual model identifier used by your LM Studio server (this can often be found in the LM Studio server logs or model selection screen). `get_langchain_llm` in `llm_services.py` has a default if `LOCAL_MODEL_NAME` is not set.

## Usage

1.  **Prepare Your Documents:**
    *   Place the PDF documents you want to include in the knowledge base into a folder. For example, you can use `medical_rag_agent/data/sample_medical_pdfs/` or create a new one.
    *   The `medical_rag_agent/data/sample_medical_pdfs/` folder contains a `dummy_document.pdf` to get started.

2.  **Build the Vector Index:**
    Use the `build_index.py` script to process your documents and create the FAISS vector index.
    ```bash
    python scripts/build_index.py --data_folder path/to/your/pdf_folder --vector_store_path path/to/your/vector_store
    ```
    *   `--data_folder`: (Required) Path to the folder containing your PDF documents.
        *   Example: `python scripts/build_index.py --data_folder data/sample_medical_pdfs/`
    *   `--vector_store_path`: (Optional) Directory where the built index will be stored.
        *   Defaults to `vector_store_prod` in the project root.
        *   Example: `python scripts/build_index.py --data_folder data/sample_medical_pdfs/ --vector_store_path my_medical_index`
    *   Other optional arguments: `--chunk_size`, `--chunk_overlap`, `--max_chars_per_section` (see script help with `-h` for details).

    This command will:
    *   Load PDFs from `--data_folder`.
    *   Chunk them using section-aware logic.
    *   Generate embeddings.
    *   Build and save the FAISS index to `--vector_store_path`.

3.  **Run the Agent CLI:**
    Once the index is built and your local LLM server is running, you can interact with the medical agent using the `run_agent_cli.py` script.
    ```bash
    python scripts/run_agent_cli.py
    ```
    *   The agent will initialize (this might take a moment).
    *   You will see a prompt: `User Query (type 'exit' or 'quit' to end):`
    *   Enter your queries. The agent will use its tools (including the RAG system) to respond.
    *   Example queries:
        *   "What are the treatment options for acute asthma exacerbation?"
        *   "Find information on managing sepsis, specifically in the 'Treatment Plan' section."
        *   (If you had a patient scenario in mind) "Patient: 30 y/o male, difficulty breathing, history of asthma. Current location: Clinic A. What are the capabilities of University Hospital for respiratory emergencies and how long would it take to get there?"

4.  **Jupyter Notebook for Exploration:**
    *   The `notebooks/1_Document_Ingestion_and_Indexing.ipynb` notebook provides a step-by-step guide through the document loading, chunking, and indexing process. This is useful for understanding the pipeline and for debugging.
    *   Ensure you have `ipykernel` installed (`pip install ipykernel`).
    *   Run Jupyter Lab or Jupyter Notebook: `jupyter lab` or `jupyter notebook`.
    *   Open and run the cells in the notebook. It defaults to using `data/sample_medical_pdfs/` and saving its index to `vector_store_notebook/`.

## Key Configuration Points

*   **`.env` file:** Crucial for configuring the LLM endpoint and model.
*   **`COMMON_SECTION_HEADERS` in `src/document_processor.py`:** This list can be customized to improve section detection for your specific document types.
*   **Embedding Model (`src/indexing.py`):** Defaults to `sentence-transformers/all-MiniLM-L6-v2`. Can be changed in `get_embedding_model()`.
*   **Chunking Parameters (`src/document_processor.py` and `scripts/build_index.py`):** `chunk_size`, `chunk_overlap`, `max_chars_per_section_chunk` can be tuned based on document characteristics and desired granularity.
*   **Agent Prompts (`src/agent/prompts.py`):** The system prompt and task templates define the agent's behavior and can be modified for different roles or tasks.

## Extending the System

*   **Add More Documents:** Place new PDFs in your data folder and rebuild the index using `scripts/build_index.py`.
*   **Add More Tools:** Define new `Tool` objects in `src/agent/tools.py` and add them to the `all_tools` list. Update the `MEDICAL_AGENT_SYSTEM_PROMPT` to inform the agent about new tools.
*   **Improve Section Headers:** Expand the `COMMON_SECTION_HEADERS` list in `src/document_processor.py` for better section detection.
*   **Different Embedding Models or Vector Stores:** Modify `src/indexing.py` to use different LlamaIndex embedding components or vector stores (e.g., ChromaDB, Weaviate).
*   **Structured Output for Agent:** Implement Pydantic models or LangChain output parsers to get structured information from the agent instead of just text responses, especially for complex tasks like the patient transfer scenario.
*   **Fine-tune LLM:** For advanced use cases, fine-tuning an open-source LLM on specific medical data could improve performance.

## Troubleshooting

*   **Connection Errors (Agent/LLM):**
    *   Ensure your local LLM server (e.g., LM Studio) is running.
    *   Verify the `OPENAI_API_BASE` in your `.env` file matches the server address (e.g., `http://localhost:1234/v1`).
    *   Check if a model is loaded and selected in your LLM server.
*   **Index Not Found:**
    *   Ensure you have run `scripts/build_index.py` (or the notebook) and it completed successfully.
    *   Verify that the `index_storage_dir` used by `query_engine.py` (and thus by the agent's RAG tool) points to the correct location of your built index (default is `vector_store_notebook/` for agent CLI if notebook was run, or `vector_store_prod/` if `build_index.py` was run with defaults). The agent CLI defaults to using `vector_store_notebook/`.
*   **Module Not Found Errors:**
    *   Make sure your virtual environment is activated.
    *   Ensure all dependencies in `requirements.txt` are installed.
    *   The scripts and modules are generally designed to handle `sys.path` for imports within the project structure. If running scripts from arbitrary locations, ensure your `PYTHONPATH` is set appropriately or run them from the project root.
*   **Poor RAG Performance:**
    *   Experiment with different chunking strategies (chunk size, overlap, section definitions).
    *   Try different embedding models.
    *   Ensure your source documents are clean and have good text quality.
    *   Refine your queries or use metadata filters.

## Metadata and Filtering

During the document chunking process (see `src/document_processor.py`), metadata is automatically added to each text node. This currently includes:

*   `file_name`: The name of the original PDF document.
*   `section`: The inferred section of the document the chunk belongs to (e.g., "Introduction", "Treatment Plan", "Default" if no specific header is matched). This is based on a predefined list of common medical/scientific section headers.
*   `original_doc_id`: The internal LlamaIndex ID of the parent document from which the node was derived.
*   `full_doc_id`: Also the internal LlamaIndex ID of the parent document (same as `original_doc_id`).
*   `chunk_in_section`: (Optional) If a large section was further split by the sentence splitter, this indicates the chunk number within that section.

This metadata can be leveraged at query time to retrieve more targeted information using LlamaIndex's `MetadataFilters`.

**Example: Filtering by Section**

If you want to search for information specifically within "Treatment Plan" sections of your documents, you can define a filter like this:

```python
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters # Or MetadataFilterCondition for AND/OR

# Define the filter
treatment_plan_filter = MetadataFilters(
    filters=[ExactMatchFilter(key="section", value="Treatment Plan")]
)

# When creating the query engine (in src/query_engine.py or your script):
# query_engine = create_query_engine(
#     index_storage_dir="path/to/your/vector_store",
#     filters=treatment_plan_filter
# )

# Now, queries made with this engine will primarily consider nodes matching the filter.
# response = query_engine.query("What is the recommended approach for X?")
```
The `query_medical_rag` tool in `src/agent/tools.py` supports a `section_filter` argument that implements this.

**Future Metadata Possibilities:**

*   `document_type`: e.g., "research_paper", "clinical_protocol", "textbook_chapter". This would require adding this information during the document loading phase or deriving it from file names/paths.
*   `keywords`: Automatically extracted keywords from each chunk using an LLM or other NLP techniques.
*   `publication_date`: If available from the source documents.

By enriching nodes with relevant metadata and applying filters, the precision of the RAG system can be significantly improved.
