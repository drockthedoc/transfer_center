import os
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike

def main():
    # Load environment variables from .env file
    # Assuming the script is in medical_rag_agent/scripts/
    # and .env is in medical_rag_agent/
    script_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    dotenv_path = os.path.join(project_root, ".env")
    load_dotenv(dotenv_path)

    openai_api_base = os.getenv("OPENAI_API_BASE")
    openai_api_key = os.getenv("OPENAI_API_KEY", "not-needed")

    if not openai_api_base:
        print("Error: OPENAI_API_BASE not found in .env file or environment variables.")
        return

    # 1. Set up the LLM
    llm = OpenAILike(
        model="local-model",  # Or any model name your local server uses
        api_base=openai_api_base,
        api_key=openai_api_key,
        is_chat_model=True, # Assuming LM Studio serves a chat model
        timeout=120 # Increased timeout for local models
    )

    # 2. Use SimpleDirectoryReader to load documents
    # Ensure the path is relative to the project root
    data_path = os.path.join(project_root, "data")
    reader = SimpleDirectoryReader(input_files=[os.path.join(data_path, "sample_text_for_indexing.txt")])
    documents = reader.load_data()

    if not documents:
        print("Error: No documents loaded. Check the data path and file.")
        return

    # 3. Use HuggingFaceEmbedding
    embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # 4. Create a ServiceContext (or use Settings in newer LlamaIndex versions)
    # In newer versions, Settings is used globally
    Settings.llm = llm
    Settings.embed_model = embed_model
    # Settings.chunk_size = 512 # Optional: configure chunk size

    # 5. Construct a VectorStoreIndex
    print("Constructing index...")
    index = VectorStoreIndex.from_documents(documents)
    print("Index constructed.")

    # 6. Create a query engine
    query_engine = index.as_query_engine(streaming=False) # streaming=False for synchronous response

    # 7. Perform a simple query
    query_text = "What is RAG?"
    print(f"Querying: {query_text}")
    try:
        response = query_engine.query(query_text)
        print("Query Response:")
        print(str(response))
    except Exception as e:
        print(f"Error during query: {e}")
        print("This might be due to the local LLM server not running or not being reachable.")
        print("Please ensure your LM Studio (or other OpenAI-compatible server) is running,")
        print(f"a model is loaded, and it's accessible at {openai_api_base}.")

if __name__ == "__main__":
    main()
