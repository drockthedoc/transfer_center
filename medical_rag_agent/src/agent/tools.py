import logging
from typing import Optional, List
from pathlib import Path

from langchain.tools import Tool
from llama_index.core.query_engine import BaseQueryEngine
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter

# Import configuration system
from config import initialize_medical_rag_config

# Initialize configuration (this handles all path setup, logging, and env loading)
config = initialize_medical_rag_config()
logger = logging.getLogger(__name__)

# Import modules using the configured paths
try:
    from query_engine import create_query_engine
except ImportError:
    logger.warning("Could not import create_query_engine directly. Trying alternative import.")
    try:
        from medical_rag_agent.src.query_engine import create_query_engine
    except ImportError as e:
        logger.error(f"Failed to import create_query_engine: {e}")
        create_query_engine = None  # Will be handled in the function


def query_medical_rag(query: str, section_filter: Optional[str] = None) -> str:
    """
    Queries the medical RAG system.
    
    Args:
        query (str): The user query.
        section_filter (Optional[str]): Optional section filter for metadata.
        
    Returns:
        str: Formatted response from the RAG system or error message.
    """
    if create_query_engine is None:
        return "RAG Tool Error: Query engine module could not be imported. Please check the project setup."
    
    # Use configuration for paths and settings
    index_storage_dir = config['vector_store_path']
    openai_api_base = config['llm_api_base']
    
    logger.info(f"RAG Tool: Using index from: {index_storage_dir}")
    logger.info(f"RAG Tool: Query: '{query}', Section Filter: '{section_filter}'")

    filters = None
    if section_filter:
        filters = MetadataFilters(filters=[ExactMatchFilter(key="section", value=section_filter)])
        logger.info(f"RAG Tool: Applying metadata filter: section = '{section_filter}'")

    try:
        index_path = Path(index_storage_dir)
        if not index_path.exists() or not (index_path / "vector_store.faiss").exists():
            error_msg = f"RAG Tool Error: Index directory or 'vector_store.faiss' not found at: {index_storage_dir}. Please ensure the index is built."
            logger.error(error_msg)
            return error_msg
            
        rag_query_engine = create_query_engine(
            index_storage_dir=index_storage_dir,
            llm_api_base=openai_api_base,
            filters=filters
        )
        
        if rag_query_engine is None:
            return "RAG Tool Error: Failed to create query engine. Index might be corrupted or inaccessible."
            
        response = rag_query_engine.query(query)
        
        # Format response
        formatted_response = ""
        if hasattr(response, 'response') and response.response:
            formatted_response += f"Response: {response.response}\n\nSources:\n"
        else:
            formatted_response += "No direct textual response from LLM (or LLM not configured). Relevant sources found:\n"
            
        if hasattr(response, 'source_nodes') and response.source_nodes:
            for i, source_node in enumerate(response.source_nodes):
                file_name = source_node.metadata.get('file_name', 'N/A')
                section = source_node.metadata.get('section', 'N/A')
                formatted_response += (
                    f"  Source {i+1}: \n"
                    f"    ID: {source_node.id_}\n"
                    f"    Score: {getattr(source_node, 'score', 0):.4f}\n"
                    f"    File: {file_name}\n"
                    f"    Section: {section}\n"
                    f"    Text: {getattr(source_node, 'text', '')[:200].strip()}...\n\n"
                )
        else:
            formatted_response += "No source documents found for this query."
            if filters:
                formatted_response += f" (Filters applied: {filters.to_dict()})"
                
        return formatted_response.strip()
        
    except Exception as e:
        logger.error(f"RAG Tool Error: Exception during query: {e}", exc_info=True)
        error_detail = str(e)
        if "Connection error" in error_detail or "refused" in error_detail.lower():
            return f"RAG Tool Error: Could not connect to LLM. Please ensure local LLM server is running. Details: {error_detail}"
        return f"RAG Tool Error: An unexpected error occurred. Details: {error_detail}"

# LangChain Tools Definition
rag_query_tool = Tool(
    name="MedicalInformationRetriever",
    func=query_medical_rag,
    description=(
        "Queries the local medical knowledge base (RAG system) for information from ingested medical "
        "documents like textbooks, clinical guidelines, and protocols. Use this to find specific medical facts, "
        "details about conditions, established treatment protocols, inclusion/exclusion criteria, etc. "
        "Input is a natural language query. You can also specify a 'section_filter' "
        "(e.g., 'Treatment Plan', 'Diagnosis', 'Introduction') as a keyword argument if you need to narrow down "
        "the search to a specific document section. "
        "Example call: MedicalInformationRetriever(query='What are the treatments for type 2 diabetes?', section_filter='Treatment Plan')"
    )
)

get_geographic_info_tool = Tool(
    name="GeographicContextTool",
    func=lambda location_query: f"Mock Geo Info: For '{location_query}', current traffic is moderate. Estimated travel time to University Hospital is 25 minutes. Weather: Light rain. Closest Level I Trauma center is City General, 15 mins away.",
    description=(
        "Provides simulated real-time geographic context, including traffic conditions, estimated travel "
        "times between points, and weather information. Input is a natural language query describing the "
        "location or route of interest (e.g., 'traffic from patient location to University Hospital', 'weather at City General')."
    )
)

get_facility_capabilities_tool = Tool(
    name="FacilityCapabilitiesTool",
    func=lambda facility_query: f"Mock Facility Info: For '{facility_query}': University Hospital is a Level I Trauma Center, has an active cardiac cath lab, comprehensive stroke center, and neurosurgery. Currently accepting all patients. City General is a Level II Trauma, no cardiac cath lab on weekends. Currently on diversion for stroke patients.",
    description=(
        "Provides simulated real-time information about a medical facility's capabilities, services, specialty "
        "units, and current operational status (e.g., diversion status for certain conditions, bed availability). "
        "Input is the facility name or a query about facilities meeting certain criteria (e.g., 'nearest Level I trauma center')."
    )
)

all_tools: List[Tool] = [rag_query_tool, get_geographic_info_tool, get_facility_capabilities_tool]

if __name__ == '__main__':
    # sys.path adjustments are at the top of the file.
    # The import for create_query_engine might need to be re-verified based on execution context.
    # If this script is run directly, the sys.path manipulation at the top should handle it.
    
    print("--- Testing RAG Query Tool ---")
    # Note: This test relies on the index built by the notebook and a running LLM server (if OPENAI_API_BASE is set)
    
    # Test 1: Query with section filter
    print("\nTest 1: Querying with section filter 'Introduction'...")
    # The dummy doc created by `document_processor.py` advanced example has "Introduction" section.
    # The one in `vector_store_notebook` (from `dummy_document.pdf`) might have "Default" or "Introduction".
    # For `dummy_document.pdf`, "This is a test PDF document... Section: Introduction. Content: Basics of RAG."
    # The section "Introduction" should contain "Content: Basics of RAG."
    # The section "Default" should contain "This is a test PDF document... Section: Introduction."
    result1 = query_medical_rag(query="What are RAG basics?", section_filter="Introduction")
    print("\nResult 1 (filtered for 'Introduction'):")
    print(result1)

    # Test 2: Query without section filter
    print("\nTest 2: Querying without section filter...")
    result2 = query_medical_rag(query="What are RAG basics?")
    print("\nResult 2 (unfiltered):")
    print(result2)
    
    # Test 3: Query for content likely in 'Default' section of dummy_document.pdf
    print("\nTest 3: Querying for content in 'Default' section...")
    result3 = query_medical_rag(query="What is this document about?", section_filter="Default")
    print("\nResult 3 (filtered for 'Default'):")
    print(result3)

    print("\n--- Testing Other Tools ---")
    geo_query = "traffic from patient location to University Hospital"
    print(f"\nTest 4: Geographic Context Tool with query: '{geo_query}'")
    geo_result = get_geographic_info_tool.run(geo_query)
    print(f"Result 4: {geo_result}")

    facility_query = "University Hospital"
    print(f"\nTest 5: Facility Capabilities Tool with query: '{facility_query}'")
    facility_result = get_facility_capabilities_tool.run(facility_query)
    print(f"Result 5: {facility_result}")

    print("\n--- Tool Testing Finished ---")
