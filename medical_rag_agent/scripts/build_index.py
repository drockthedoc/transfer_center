import argparse
import logging
from pathlib import Path
import sys

# Add the project root to sys.path to import config
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import configuration system
from src.config import initialize_medical_rag_config

def main():
    """
    CLI entrypoint for building a vector index from PDF documents.
    Uses centralized configuration management.
    """
    # Initialize configuration (handles .env loading, logging, and paths)
    config = initialize_medical_rag_config()
    logger = logging.getLogger(__name__)
    
    # Import modules after configuration is set up
    try:
        from src.document_processor import load_pdfs_from_folder, chunk_documents
        from src.indexing import get_embedding_model, build_vector_index
    except ImportError as e:
        logger.error(f"Failed to import necessary modules: {e}")
        return

    parser = argparse.ArgumentParser(description="Build a vector index from PDF documents.")
    parser.add_argument(
        "--data_folder",
        type=str,
        required=True,
        help="Path to the folder containing PDF files to index."
    )
    parser.add_argument(
        "--vector_store_path",
        type=str,
        default="vector_store_prod",
        help="Path to the directory where the vector index will be stored. Default: 'vector_store_prod'."
    )
    parser.add_argument(
        "--chunk_size",
        type=int,
        default=1024, # Default from document_processor.chunk_documents
        help="Default chunk size for sentence splitting if sections are too large or no sections are found. Default: 1024."
    )
    parser.add_argument(
        "--chunk_overlap",
        type=int,
        default=200, # Default from document_processor.chunk_documents
        help="Default chunk overlap for sentence splitting. Default: 200."
    )
    parser.add_argument(
        "--max_chars_per_section", # Matches the prompt's naming for the argument
        type=int,
        default=4000, # Default from document_processor.chunk_documents for 'max_chars_per_section_chunk'
        help="Maximum characters for a chunk derived directly from a section before sentence splitting is applied. Default: 4000."
    )
    
    args = parser.parse_args()

    # Resolve paths to absolute paths for robustness
    data_folder_path = Path(args.data_folder).resolve()
    vector_store_path = Path(args.vector_store_path).resolve()
    
    logging.info("Starting the indexing process...")
    logging.info(f"Data folder: {data_folder_path}")
    logging.info(f"Vector store path: {vector_store_path}")
    
    # Validate paths
    if not data_folder_path.exists():
        logging.error(f"Data folder does not exist: {data_folder_path}")
        return
    if not data_folder_path.is_dir():
        logging.error(f"Data folder is not a directory: {data_folder_path}")
        return

    # 1. Load PDFs
    logging.info(f"Loading PDF documents from: {data_folder_path}")
    try:
        documents = load_pdfs_from_folder(str(data_folder_path))
        if not documents:
            logging.warning(f"No documents found in {data_folder_path}. Exiting.")
            return
        logging.info(f"Loaded {len(documents)} document(s).")
    except Exception as e:
        logging.error(f"Failed to load documents: {e}", exc_info=True)
        return

    # 2. Chunk Documents
    logging.info("Chunking documents...")
    try:
        nodes = chunk_documents(
            documents,
            default_chunk_size=args.chunk_size,
            default_chunk_overlap=args.chunk_overlap,
            max_chars_per_section_chunk=args.max_chars_per_section
        )
        if not nodes:
            logging.warning("No nodes were created after chunking. Exiting.")
            return
        logging.info(f"Chunked documents into {len(nodes)} nodes.")
    except Exception as e:
        logging.error(f"Failed to chunk documents: {e}", exc_info=True)
        return

    # 3. Get Embedding Model
    logging.info("Initializing embedding model...")
    try:
        embed_model = get_embedding_model()
        logging.info(f"Embedding model '{embed_model.model_name}' initialized.")
    except Exception as e:
        logging.error(f"Failed to initialize embedding model: {e}", exc_info=True)
        return

    # 4. Build Vector Index
    logging.info(f"Building vector index and persisting to: {vector_store_path}")
    try:
        index = build_vector_index(nodes, embed_model, storage_persist_dir=str(vector_store_path))
        if index:
            logging.info(f"Successfully built and persisted vector index at: {vector_store_path}")
        else:
            logging.error("Failed to build vector index. build_vector_index returned None.")
            return
    except Exception as e:
        logging.error(f"Failed to build vector index: {e}", exc_info=True)
        return
    
    logging.info("Indexing process completed successfully.")

if __name__ == "__main__":
    main()
