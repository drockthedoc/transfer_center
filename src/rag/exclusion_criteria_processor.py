import os
import sys
import yaml
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from dotenv import load_dotenv

# Ensure the project root is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv(os.path.join(project_root, '.env'))

# Configuration
EXCLUSION_CRITERIA_YAML_PATH = os.path.join(project_root, 'data', 'exclusion_criteria.yaml')
VECTOR_STORE_DIR = os.path.join(project_root, 'vector_stores')
EXCLUSION_CRITERIA_VS_PATH = os.path.join(VECTOR_STORE_DIR, 'exclusion_criteria_faiss')
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def load_exclusion_criteria(file_path: str):
    """Loads exclusion criteria from a YAML file with nested structure."""
    all_criteria_items = []
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        if not data:
            print(f"Warning: YAML file {file_path} is empty or could not be parsed correctly.")
            return []

        # Iterate through top-level keys (campuses)
        for campus_name, campus_data in data.items():
            # ADDED: Mapping from YAML keys to TARGET_HOSPITAL_KEYS
            campus_key_map = {
                "west_campus": "TCH_WEST_KATY",
                "the_woodlands_campus": "TCH_WOODLANDS",
                "TCH_NORTH_AUSTIN": "TCH_NORTH_AUSTIN" # Corrected: YAML key is TCH_NORTH_AUSTIN
                # Add other mappings here if new campus sections are added to YAML
            }
            # Use the mapped key if available, otherwise use the original (for general info etc.)
            mapped_campus_name = campus_key_map.get(campus_name, campus_name)

            if not isinstance(campus_data, dict):
                # Skip non-dictionary top-level items like 'community_sites_general_info'
                continue
            
            # Iterate through categories within the campus
            for category_key, category_data in campus_data.items():
                if isinstance(category_data, dict) and 'criteria' in category_data and isinstance(category_data['criteria'], list):
                    category_title = category_data.get('category_title', category_key) # Use category_key as fallback
                    for criterion_dict in category_data['criteria']:
                        if isinstance(criterion_dict, dict):
                            # Add campus and category info to the criterion item
                            criterion_dict['campus_name'] = mapped_campus_name
                            criterion_dict['category_title'] = category_title
                            all_criteria_items.append(criterion_dict)
                        else:
                            print(f"Warning: Found non-dictionary item in criteria list for {mapped_campus_name} -> {category_key}")
        
        if not all_criteria_items:
            print(f"Warning: No exclusion criteria items found after parsing {file_path}. Check YAML structure.")
        return all_criteria_items

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return []
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {file_path}: {e}")
        return []

def create_langchain_documents(criteria_list: list):
    """Transforms a list of criteria dictionaries into LangChain Document objects."""
    documents = []
    for criterion_item in criteria_list:
        content = criterion_item.get('condition', '') 
        search_keywords = criterion_item.get('search_keywords', [])
        if isinstance(search_keywords, list) and search_keywords:
            content += " " + " ".join(search_keywords)
        
        metadata = {
            'id': criterion_item.get('id'), 
            'hospital_id': criterion_item.get('campus_name'), 
            'criterion_category': criterion_item.get('category_title'), 
            'sub_category': criterion_item.get('sub_category'), 
            'disposition': criterion_item.get('disposition'),
            'notes': criterion_item.get('notes'),
            'original_criterion': criterion_item.get('condition', ''), 
            'source_file': os.path.basename(EXCLUSION_CRITERIA_YAML_PATH) 
        }
        # Filter out None values from metadata
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        documents.append(Document(page_content=content.strip(), metadata=metadata))
    return documents

def build_and_save_vector_store(documents: list, embedding_model_name: str, save_path: str):
    """Builds a FAISS vector store from documents and saves it to disk."""
    if not documents:
        print("No documents to process. Vector store not created.")
        return None

    print(f"Initializing embeddings with model: {embedding_model_name}")
    embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)
    
    print(f"Building FAISS vector store with {len(documents)} documents...")
    vector_store = FAISS.from_documents(documents, embeddings)
    
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    print(f"Saving vector store to {save_path}...")
    vector_store.save_local(save_path)
    print("Vector store saved successfully.")
    return vector_store

def load_vector_store(load_path: str, embedding_model_name: str):
    """Loads a FAISS vector store from disk."""
    if not os.path.exists(load_path):
        print(f"Vector store not found at {load_path}. Please build it first.")
        return None
    print(f"Loading vector store from {load_path}...")
    embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)
    vector_store = FAISS.load_local(load_path, embeddings, allow_dangerous_deserialization=True)
    print("Vector store loaded successfully.")
    return vector_store


if __name__ == '__main__':
    print("Processing exclusion criteria for RAG system...")
    
    # 1. Load exclusion criteria
    criteria_data = load_exclusion_criteria(EXCLUSION_CRITERIA_YAML_PATH)
    if not criteria_data:
        print("No exclusion criteria data loaded. Exiting.")
        sys.exit(1)
    
    # 2. Create LangChain Documents
    langchain_documents = create_langchain_documents(criteria_data)
    if not langchain_documents:
        print("No LangChain documents created. Exiting.")
        sys.exit(1)
    print(f"Created {len(langchain_documents)} LangChain documents.")

    # 3. Build and save the vector store
    vs = build_and_save_vector_store(langchain_documents, EMBEDDING_MODEL_NAME, EXCLUSION_CRITERIA_VS_PATH)
    
    if vs:
        print("\nTesting the vector store with a sample query...")
        query = "patient requires ventilator support"
        try:
            results = vs.similarity_search_with_score(query, k=3)
            if results:
                print(f"Top 3 results for query: '{query}'")
                for doc, score in results:
                    print(f"  ID: {doc.metadata.get('id')}, Score: {score:.4f}, Criterion: {doc.metadata.get('original_criterion')}")
            else:
                print("No results found for the sample query.")
        except Exception as e:
            print(f"Error during similarity search: {e}")
    
    print("\nExclusion criteria processing complete.")
