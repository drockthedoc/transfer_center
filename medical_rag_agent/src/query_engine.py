import os
import sys
import logging
from pathlib import Path
from typing import Optional

from llama_index.core import ServiceContext, Settings
from llama_index.core.query_engine import BaseQueryEngine
from llama_index.llms.openai_like import OpenAILike
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter

# Import configuration system
from config import initialize_medical_rag_config

# Initialize configuration (this handles all path setup, logging, and env loading)
config = initialize_medical_rag_config()
logger = logging.getLogger(__name__)

# Import modules using the configured paths
from indexing import get_embedding_model, load_vector_index

def create_query_engine(
    index_storage_dir: str,
    embed_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    llm_api_base: Optional[str] = None,
    llm_api_key: Optional[str] = "not-needed",
    llm_model_name: Optional[str] = "local-model",
    filters: Optional[MetadataFilters] = None
) -> Optional[BaseQueryEngine]:
    """
    Creates and returns a query engine from a persisted LlamaIndex.

    Args:
        index_storage_dir (str): Directory where the index is stored.
        embed_model_name (str): Name of the sentence transformer model for embeddings.
        llm_api_base (Optional[str]): API base URL for the LLM. If None, LLM is not configured.
        llm_api_key (Optional[str]): API key for the LLM.
        llm_model_name (Optional[str]): Model name for the LLM.
        filters (Optional[MetadataFilters]): Metadata filters to apply to the query engine.

    Returns:
        Optional[BaseQueryEngine]: The query engine, or None if index loading fails.

    Raises:
        FileNotFoundError: If the index directory or FAISS file is missing.
    """
    logging.info(f"Initializing query engine with index from: {index_storage_dir}")
    try:
        embed_model = get_embedding_model(embed_model_name)
        logging.info(f"Embedding model '{embed_model_name}' loaded.")

        index = load_vector_index(storage_persist_dir=index_storage_dir, embed_model=embed_model)
        if index is None:
            logging.error(f"Failed to load index from {index_storage_dir}. Query engine creation aborted.")
            return None
        logging.info("Vector index loaded successfully.")
    except FileNotFoundError as e:
        logging.error(str(e))
        return None
    except Exception as e:
        logging.error(f"Unexpected error loading index: {e}")
        return None

    llm = None
    if llm_api_base:
        llm = OpenAILike(
            api_base=llm_api_base,
            api_key=llm_api_key,
            model=llm_model_name,
            is_chat_model=True,
            http_client_options={"timeout": 120.0}
        )
        logging.info(f"LLM configured: model='{llm_model_name}', api_base='{llm_api_base}'")
    else:
        logging.info("No LLM API base provided. Query engine will use retrieval capabilities only.")

    service_context = ServiceContext.from_defaults(embed_model=embed_model, llm=llm)
    
    query_engine = index.as_query_engine(
        service_context=service_context,
        filters=filters # Pass filters here
    )
    logging.info(f"Query engine created. Filters: {filters.to_dict() if filters else 'None'}")
    
    return query_engine

if __name__ == '__main__':
    # Configuration is already initialized at module level via initialize_medical_rag_config()
    notebook_index_dir = config['paths']['vector_store_dir']

    if not notebook_index_dir.exists() or not (notebook_index_dir / "vector_store.faiss").exists():
        logger.error(f"Index directory or 'vector_store.faiss' not found at: {notebook_index_dir}")
        logger.error("Please ensure you have run the '1_Document_Ingestion_and_Indexing.ipynb' notebook ")
        logger.error("to generate the vector index before running this script.")
        sys.exit(1)

    llm_api_base_from_env = config['llm_api_base']
    llm_api_key_from_env = os.getenv("OPENAI_API_KEY", "not-needed")
    
    if not llm_api_base_from_env:
        logger.warning("OPENAI_API_BASE not found in environment. LLM will not be configured for querying.")

    query_text = "What are RAG basics?" # Define query_text
    
    # Example of using MetadataFilters
    # The dummy_document.pdf's text ("This is a test PDF document... Section: Introduction. Content: Basics of RAG.")
    # when processed by document_processor.py's advanced chunker, the content before "Section: Introduction"
    # (if "Section: Introduction" is not matched by HEADER_REGEX) gets "Default" section.
    # The content "Content: Basics of RAG." under "Section: Introduction" would get "Introduction" section.
    # Let's use "Default" as it's more likely to exist with the current dummy PDF.
    specific_section_filter = MetadataFilters(
        filters=[ExactMatchFilter(key="section", value="Default")],
    )
    print(f"Attempting query with filter for section='Default'")

    # Create query engine WITH the filter
    query_engine_filtered = create_query_engine(
        index_storage_dir=str(notebook_index_dir),
        llm_api_base=llm_api_base_from_env,
        llm_api_key=llm_api_key_from_env,
        filters=specific_section_filter # Pass the filter object
    )

    if query_engine_filtered:
        logger.info(f"Querying with filter: {specific_section_filter.to_dict()}")
        try:
            filtered_response = query_engine_filtered.query(query_text)
            print("Filtered Response:")
            if hasattr(filtered_response, 'response') and filtered_response.response:
                print(filtered_response.response)
            else:
                # If no direct response text (e.g., if LLM is None or query is purely retrieval)
                print("No direct response text. Source nodes (if any):")
            
            if filtered_response.source_nodes:
                for node in filtered_response.source_nodes:
                    print(f"  ID: {node.id_}, Score: {node.score:.4f}, Section: {node.metadata.get('section', 'N/A')}")
                    print(f"  Text: {node.text[:150].strip()}...") # Print snippet of source node
            else:
                print("  No source nodes found for the filtered query.")

        except Exception as e:
            logger.error(f"Error during filtered query: {e}")
            if "Connection error" in str(e) or isinstance(e, ConnectionError): # More robust check
                 logger.error("This is likely due to the local LLM server not running. The query was attempted with filters.")
    else:
        logger.error("Could not create filtered query engine.")
    
    # Original unfiltered query for comparison (optional, can be uncommented)
    # print("\nAttempting original unfiltered query...")
    # query_engine_unfiltered = create_query_engine(
    #     index_storage_dir=str(notebook_index_dir),
    #     llm_api_base=llm_api_base_from_env,
    #     llm_api_key=llm_api_key_from_env
    # )
    # if query_engine_unfiltered:
    #     logger.info(f"Performing sample query (unfiltered): '{query_text}'")
    #     try:
    #         response_unfiltered = query_engine_unfiltered.query(query_text)
    #         if hasattr(response_unfiltered, 'response'):
    #             logger.info(f"Unfiltered Query Response: {response_unfiltered.response}")
    #         else:
    #             logger.info(f"Unfiltered Query Response (raw): {response_unfiltered}")
    #     except Exception as e:
    #         logger.error(f"Error during unfiltered query: {e}")
    # else:
    #     logger.error("Unfiltered query engine could not be created.")

    logger.info("Query engine script finished.")
