import os
import faiss # faiss-cpu
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    ServiceContext, # Older LlamaIndex; Settings is newer
    load_index_from_storage,
    Settings 
)
from llama_index.core.schema import BaseNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore
from typing import List

def get_embedding_model(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> HuggingFaceEmbedding:
    """
    Creates and returns a HuggingFaceEmbedding model.

    Args:
        model_name (str): The name of the Hugging Face sentence transformer model.

    Returns:
        HuggingFaceEmbedding: The embedding model instance.
    """
    return HuggingFaceEmbedding(model_name=model_name)

def build_vector_index(
    nodes: List[BaseNode], 
    embed_model: HuggingFaceEmbedding, 
    storage_persist_dir: str = "vector_store"
) -> VectorStoreIndex:
    """
    Builds a FAISS VectorStoreIndex from a list of nodes and persists it to disk.

    Args:
        nodes (List[BaseNode]): The list of BaseNode objects to index.
        embed_model (HuggingFaceEmbedding): The embedding model to use.
        storage_persist_dir (str): The directory to persist the index and vector store.

    Returns:
        VectorStoreIndex: The constructed VectorStoreIndex.

    Raises:
        FileNotFoundError: If the storage directory cannot be created.
    """
    if not os.path.exists(storage_persist_dir):
        try:
            os.makedirs(storage_persist_dir)
        except Exception as e:
            raise FileNotFoundError(f"Could not create storage directory: {storage_persist_dir}. Error: {e}")

    # Define path for the FAISS index file
    faiss_path = os.path.join(storage_persist_dir, "vector_store.faiss")

    # 1. Create FaissVectorStore
    # embed_dim can be obtained from the embed_model after it's loaded,
    # or often models have a fixed dimension (e.g., all-MiniLM-L6-v2 has 384)
    # For robustness, it's better to get it from the model if possible,
    # but HuggingFaceEmbedding doesn't directly expose embed_dim before first use.
    # We'll assume a common dimension or rely on FAISS to adapt if it can.
    # A common way is to run a dummy embedding:
    # test_emb = embed_model.get_text_embedding("test")
    # embed_dim = len(test_emb)
    # However, to avoid running an embedding here, we use a common default.
    # all-MiniLM-L6-v2 has an embedding dimension of 384.
    # It's crucial that this matches the actual model's dimension.
    # A more robust way would be to pass embed_dim as an argument if known,
    # or ensure embed_model is initialized and queried once before this.
    
    # Let's try to get embed_dim by embedding a dummy text
    try:
        dummy_text_embedding = embed_model.get_text_embedding("hello world")
        embed_dim = len(dummy_text_embedding)
    except Exception as e:
        print(f"Could not determine embedding dimension dynamically, defaulting to 384. Error: {e}")
        embed_dim = 384 # Fallback for all-MiniLM-L6-v2

    faiss_index = faiss.IndexFlatL2(embed_dim)
    vector_store = FaissVectorStore(faiss_index=faiss_index)

    # 2. Create StorageContext
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # 3. Create ServiceContext (or use global Settings)
    # For older LlamaIndex versions, ServiceContext is used.
    # For newer versions, Settings.llm and Settings.embed_model are set globally.
    service_context = ServiceContext.from_defaults(embed_model=embed_model, llm=None)
    # Alternatively, using global settings:
    # Settings.llm = None # No LLM needed for indexing
    # Settings.embed_model = embed_model # Already set if get_embedding_model modified Settings

    # 4. Build VectorStoreIndex
    print(f"Building index with {len(nodes)} nodes...")
    index = VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        service_context=service_context # Use service_context if defined, otherwise relies on global Settings
    )
    print("Index built.")

    # 5. Persist the index
    # The StorageContext's persist method should handle persisting the FaissVectorStore as well,
    # if the FaissVectorStore object has a `persist` method and is correctly registered.
    # LlamaIndex's FaissVectorStore is designed to be persistable this way.
    # The actual FAISS index file (vector_store.faiss) should be saved by the FaissVectorStore's
    # own persistence logic, typically invoked by the StorageContext.
    print(f"Persisting index to: {storage_persist_dir}")
    index.storage_context.persist(persist_dir=storage_persist_dir)
    # The FaissVectorStore itself should persist its index to its _persist_path if set,
    # or to a default location within the storage_context.
    # Let's ensure the faiss_path is used by vector_store if not automatic.
    # vector_store.persist(persist_path=faiss_path) # This might be redundant if StorageContext handles it.
                                                 # LlamaIndex aims for StorageContext to manage this.
    
    if os.path.exists(faiss_path):
        print(f"FAISS index successfully saved at: {faiss_path}")
    else:
        print(f"Warning: FAISS index file was not found at {faiss_path} after persist. Check LlamaIndex version behavior.")
        # Attempt explicit persistence if the main one didn't create the file as expected.
        # This can happen if the vector_store isn't automatically persisted to the *exact* `faiss_path` name
        # by the index.storage_context.persist call alone.
        # However, FaissVectorStore's `persist` is usually called by `StorageContext`.
        # If storage_context.persist() works as expected, it should save all components.
        # The `FaissVectorStore` itself might save to a default file name like `faiss_vector_store.faiss`
        # or just `vector_store.faiss` if not specified.
        # The provided `faiss_path` might need to be passed to `FaissVectorStore` constructor if possible,
        # or check its default save name.
        # For now, we rely on StorageContext doing the right thing.

    print("Index persisted.")
    return index

def load_vector_index(
    storage_persist_dir: str = "vector_store", 
    embed_model: HuggingFaceEmbedding = None
) -> VectorStoreIndex:
    """
    Loads a FAISS VectorStoreIndex from disk.

    Args:
        storage_persist_dir (str): The directory from which to load the index.
        embed_model (HuggingFaceEmbedding): The embedding model to use. 
                                          Must be the same as used during indexing.

    Returns:
        VectorStoreIndex: The loaded VectorStoreIndex.

    Raises:
        FileNotFoundError: If the storage directory or FAISS file is missing.
    """
    if not os.path.exists(storage_persist_dir):
        raise FileNotFoundError(f"Storage directory {storage_persist_dir} not found.")
    
    faiss_path = os.path.join(storage_persist_dir, "vector_store.faiss")
    if not os.path.exists(faiss_path):
        # Attempt to find other common FAISS store names if the specific one isn't there
        # This can happen if the FaissVectorStore saved with a default name.
        potential_default_faiss_path = os.path.join(storage_persist_dir, "faiss_vector_store.faiss")
        if os.path.exists(potential_default_faiss_path):
            faiss_path = potential_default_faiss_path
            print(f"Found FAISS index at default location: {faiss_path}")
        else:
            print(f"Error: FAISS index file {faiss_path} (and default) not found in {storage_persist_dir}.")
            return None

    # 1. Create ServiceContext (or use global Settings)
    if embed_model is None: # If no model passed, try to get default
        embed_model = get_embedding_model() 
        
    service_context = ServiceContext.from_defaults(embed_model=embed_model, llm=None)
    # Using global settings:
    # Settings.llm = None
    # Settings.embed_model = embed_model

    # 2. Load FaissVectorStore
    # The vector_store needs to be loaded *before* StorageContext if it's not automatically found by StorageContext.
    # However, the more modern LlamaIndex pattern is to let StorageContext discover persisted stores.
    # Let's try the recommended way: load storage_context first, then load index.
    # The FaissVectorStore can be loaded implicitly by `load_index_from_storage` if correctly persisted.

    # Create a FaissVectorStore instance that will load from the path
    vector_store = FaissVectorStore.from_persist_path(faiss_path)
    
    # 3. Load StorageContext
    # We provide the loaded vector_store to ensure it's used.
    # persist_dir is crucial for loading other components like docstore, index_store.
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store, 
        persist_dir=storage_persist_dir
    )
    
    # 4. Load VectorStoreIndex
    print(f"Loading index from: {storage_persist_dir}")
    index = load_index_from_storage(
        storage_context=storage_context,
        service_context=service_context # Use service_context if defined, otherwise relies on global Settings
    )
    print("Index loaded.")
    return index

if __name__ == '__main__':
    # Example usage for testing only
    from document_processor import load_pdfs_from_folder, chunk_documents # Assuming in the same directory or PYTHONPATH
    import shutil

    print("Indexing Example")
    
    # Setup paths (assuming script is in src/, data/ is at project_root/data)
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_script_dir)
    
    # Use the sample_medical_pdfs folder
    pdf_folder = os.path.join(project_root, "data", "sample_medical_pdfs")
    storage_dir_name = "test_vector_store" # Use a test-specific directory
    storage_persist_path = os.path.join(project_root, "src", storage_dir_name) # Persist in src for this example

    # Ensure dummy PDF exists for testing
    dummy_pdf_target_folder = pdf_folder
    dummy_pdf_filename = "dummy_document_for_indexing.pdf"
    dummy_pdf_path_target = os.path.join(dummy_pdf_target_folder, dummy_pdf_filename)

    if not os.path.exists(dummy_pdf_target_folder):
        os.makedirs(dummy_pdf_target_folder)
    
    # Create a dummy PDF for the test
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        c = canvas.Canvas(dummy_pdf_path_target, pagesize=letter)
        c.drawString(100, 750, "This is a test PDF for indexing.py.")
        c.drawString(100, 735, "Content about FAISS and LlamaIndex.")
        c.save()
        print(f"Created dummy PDF for testing: {dummy_pdf_path_target}")
    except ImportError:
        print("reportlab not found, cannot create dummy PDF for indexing test.")
        # Fallback to skip test if PDF cannot be created
        exit()
    except Exception as e:
        print(f"Error creating dummy PDF: {e}")
        exit()

    # Clean up previous test storage if it exists
    if os.path.exists(storage_persist_path):
        print(f"Removing existing test storage: {storage_persist_path}")
        shutil.rmtree(storage_persist_path)

    # 1. Load and Chunk Documents
    print(f"Loading PDFs from: {pdf_folder}")
    documents = load_pdfs_from_folder(pdf_folder)
    if not documents:
        print(f"No documents found in {pdf_folder}. Exiting test.")
        exit()
    
    print(f"Loaded {len(documents)} documents.")
    nodes = chunk_documents(documents)
    if not nodes:
        print("No nodes created after chunking. Exiting test.")
        exit()
    print(f"Chunked into {len(nodes)} nodes.")

    # 2. Get Embedding Model
    print("Getting embedding model...")
    embed_model = get_embedding_model()
    print(f"Embedding model loaded: {embed_model.model_name}")

    # 3. Build Vector Index
    print("Building vector index...")
    index = build_vector_index(nodes, embed_model, storage_persist_dir=storage_persist_path)
    if index:
        print("Vector index built and persisted successfully.")
    else:
        print("Failed to build vector index.")
        exit()

    # 4. Load Vector Index (simulate loading in a new session)
    print("\nAttempting to load vector index from disk...")
    # Pass the same embed_model instance; in a real app, you'd re-initialize it.
    loaded_index = load_vector_index(storage_persist_dir=storage_persist_path, embed_model=embed_model)
    if loaded_index:
        print("Vector index loaded successfully from disk.")
        # Optional: Test query
        # Settings.llm = OpenAILike(api_base="http://localhost:1234/v1", api_key="fake", model="local") # Dummy LLM
        # query_engine = loaded_index.as_query_engine()
        # response = query_engine.query("What is FAISS?")
        # print(f"Query response from loaded index: {response}")
    else:
        print("Failed to load vector index from disk.")

    # Clean up test PDF and storage directory
    # if os.path.exists(dummy_pdf_path_target):
    #     os.remove(dummy_pdf_path_target)
    # if os.path.exists(storage_persist_path):
    #     shutil.rmtree(storage_persist_path)
    # print("Cleaned up test files and directory.")
    
    print("\nIndexing Example Finished.")
