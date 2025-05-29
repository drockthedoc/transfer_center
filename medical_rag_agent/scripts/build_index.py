import argparse
import os
import sys
import logging
from pathlib import Path

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # Path Setup
    # Assuming this script is in 'medical_rag_agent/scripts/'
    SCRIPT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = SCRIPT_DIR.parent  # This should be 'medical_rag_agent/'

    # Add project root to sys.path to allow 'from src...' style imports
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
        logging.info(f"Added {PROJECT_ROOT} to sys.path")

    try:
        from src.document_processor import load_pdfs_from_folder, chunk_documents
        from src.indexing import get_embedding_model, build_vector_index
    except ImportError as e:
        logging.error(f"Failed to import necessary modules from src: {e}. Ensure PYTHONPATH is set correctly or the script is run from a context where 'src' is discoverable.")
        print(f"[FATAL ERROR] Could not import modules from 'src'. Please check project structure and PYTHONPATH. Error: {e}")
        sys.exit(1)

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

    # Resolve relative paths for data_folder and vector_store_path to be absolute or relative to CWD
    # It's often better to make them absolute if the script might be called from various locations,
    # or clearly define they are relative to where the script is run.
    # For simplicity, we'll assume paths are correctly passed (e.g., relative to CWD or absolute).
    # Path(args.data_folder).resolve()
    # Path(args.vector_store_path).resolve()

    logging.info("Starting the indexing process...")
    print(f"Starting indexing process. Data folder: '{args.data_folder}', Vector store path: '{args.vector_store_path}'")

    # 1. Load PDFs
    logging.info(f"Loading PDF documents from: {args.data_folder}")
    try:
        documents = load_pdfs_from_folder(args.data_folder)
        if not documents:
            logging.warning(f"No documents found in {args.data_folder}. Exiting.")
            print(f"No PDF documents found in '{args.data_folder}'. Please check the path.")
            return
        logging.info(f"Loaded {len(documents)} document(s).")
        print(f"Successfully loaded {len(documents)} document(s).")
    except Exception as e:
        logging.error(f"Failed to load documents: {e}", exc_info=True)
        print(f"Error loading documents from '{args.data_folder}': {e}")
        return

    # 2. Chunk Documents
    logging.info("Chunking documents...")
    print("Chunking documents...")
    try:
        nodes = chunk_documents(
            documents,
            default_chunk_size=args.chunk_size,
            default_chunk_overlap=args.chunk_overlap,
            max_chars_per_section_chunk=args.max_chars_per_section # Passed to the correct parameter in chunk_documents
        )
        if not nodes:
            logging.warning("No nodes were created after chunking. Exiting.")
            print("Document chunking resulted in no nodes. Please check document content and chunking parameters.")
            return
        logging.info(f"Chunked documents into {len(nodes)} nodes.")
        print(f"Successfully chunked documents into {len(nodes)} nodes.")
    except Exception as e:
        logging.error(f"Failed to chunk documents: {e}", exc_info=True)
        print(f"Error chunking documents: {e}")
        return

    # 3. Get Embedding Model
    logging.info("Initializing embedding model...")
    print("Initializing embedding model...")
    try:
        embed_model = get_embedding_model() # Using default model
        logging.info(f"Embedding model '{embed_model.model_name}' initialized.")
        print(f"Embedding model '{embed_model.model_name}' initialized.")
    except Exception as e:
        logging.error(f"Failed to initialize embedding model: {e}", exc_info=True)
        print(f"Error initializing embedding model: {e}")
        return

    # 4. Build Vector Index
    logging.info(f"Building vector index and persisting to: {args.vector_store_path}")
    print(f"Building vector index. This may take some time. Output directory: '{args.vector_store_path}'")
    try:
        index = build_vector_index(nodes, embed_model, storage_persist_dir=args.vector_store_path)
        if index:
            logging.info(f"Successfully built and persisted vector index at: {args.vector_store_path}")
            print(f"\nSuccessfully built and persisted vector index at: {Path(args.vector_store_path).resolve()}")
        else:
            logging.error(f"Failed to build vector index. build_vector_index returned None.")
            print(f"Failed to build vector index. Please check logs for details.")
            return
    except Exception as e:
        logging.error(f"Failed to build vector index: {e}", exc_info=True)
        print(f"Error building vector index: {e}")
        return
    
    logging.info("Indexing process completed.")
    print("Indexing process completed.")

if __name__ == "__main__":
    main()
