import json
from typing import List, Dict, Any
import os

from langchain_community.docstore.document import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

# Configuration for embeddings
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# Directory to save/load FAISS index (relative to project root)
FAISS_INDEX_DIR = "vector_stores/exclusion_criteria_faiss"

def load_exclusion_criteria_documents(file_path: str) -> List[Document]:
    """Loads exclusion criteria from the JSON file and transforms them into LangChain Documents."""
    documents = []
    try:
        with open(file_path, 'r') as f:
            all_data = json.load(f)
            # Access the nested 'campuses' dictionary
            all_criteria_data = all_data.get("campuses")
            if not isinstance(all_criteria_data, dict):
                print(f"Error: 'campuses' key not found or is not a dictionary in {file_path}")
                return []
    except FileNotFoundError:
        print(f"Error: Exclusion criteria file not found at {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return []

    for hospital_id, hospital_data in all_criteria_data.items():
        criteria_block = hospital_data.get("criteria")
        if not criteria_block:
            print(f"Warning: No 'criteria' block found for {hospital_id} in {file_path}")
            continue

        # Process general exclusions
        for criterion_text in criteria_block.get("general_exclusions", []):
            metadata = {
                "hospital_id": hospital_id,
                "criterion_type": "general",
                "source_file": os.path.basename(file_path)
            }
            documents.append(Document(page_content=criterion_text, metadata=metadata))

        # Process departmental exclusions
        for dept_name, dept_data in criteria_block.get("departments", {}).items():
            for criterion_text in dept_data.get("exclusions", []):
                metadata = {
                    "hospital_id": hospital_id,
                    "criterion_type": "departmental",
                    "department_name": dept_name,
                    "source_file": os.path.basename(file_path)
                }
                documents.append(Document(page_content=criterion_text, metadata=metadata))
    
    print(f"Loaded {len(documents)} exclusion criteria documents from {file_path}")
    return documents

def get_exclusion_criteria_retriever():
    """
    Loads the pre-built FAISS vector store for exclusion criteria and returns a retriever.
    The vector store is expected to be created by 'src/rag/exclusion_criteria_processor.py'.
    """
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    full_faiss_index_path = os.path.join(project_root, FAISS_INDEX_DIR)

    if os.path.exists(full_faiss_index_path) and os.listdir(full_faiss_index_path):
        print(f"Loading existing FAISS index from {full_faiss_index_path}")
        try:
            vector_store = FAISS.load_local(full_faiss_index_path, embeddings, allow_dangerous_deserialization=True)
            print("FAISS index loaded successfully.")
            return vector_store.as_retriever()
        except Exception as e:
            print(f"Error loading FAISS index from {full_faiss_index_path}: {e}")
            print("Please ensure the index has been created by running 'src/rag/exclusion_criteria_processor.py'.")
            return None
    else:
        print(f"FAISS index not found at {full_faiss_index_path} or directory is empty.")
        print("Please create the index by running 'python -m src.rag.exclusion_criteria_processor'.")
        return None

if __name__ == '__main__':
    print("Testing RAG components setup (loading pre-built index)...")
    
    retriever = get_exclusion_criteria_retriever()
    if retriever:
        print("Successfully obtained retriever.")
        print("\nAttempting a sample retrieval...")
        try:
            sample_query = "Patient requires ventilator support"
            retrieved_docs = retriever.invoke(sample_query)
            print(f"Retrieved {len(retrieved_docs)} documents for query: '{sample_query}'")
            if retrieved_docs:
                for i, doc in enumerate(retrieved_docs[:3]): # Print top 3
                    print(f"  Retrieved Doc {i+1}: Content='{doc.page_content[:100]}...', Metadata={doc.metadata}")
            else:
                print("No documents retrieved for the sample query.")
        except Exception as e:
            print(f"Error during sample retrieval: {e}")
    else:
        print("Failed to obtain retriever. Ensure 'src/rag/exclusion_criteria_processor.py' has been run.")
    
    project_root_for_test = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    print(f"\nFAISS index is expected at: {os.path.join(project_root_for_test, FAISS_INDEX_DIR)}")
