import sys
import os
import logging
from pathlib import Path

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # Path Setup
    SCRIPT_DIR = Path(__file__).resolve().parent # medical_rag_agent/scripts/
    PROJECT_ROOT = SCRIPT_DIR.parent # This should be 'medical_rag_agent'
    # SRC_DIR = PROJECT_ROOT / "src" # Not strictly needed if PROJECT_ROOT is in path for `from src...`

    # Add project root to sys.path to allow 'from src...' style imports
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    
    # Now import create_medical_agent
    try:
        from src.agent.agent import create_medical_agent
    except ImportError as e:
        logging.error(f"Failed to import create_medical_agent: {e}. Ensure the 'src' directory and its contents are structured correctly and PROJECT_ROOT is in sys.path.")
        print(f"[FATAL ERROR] Could not import necessary modules. Please check project structure and PYTHONPATH. Error: {e}")
        return

    logging.info("Initializing Medical RAG Agent. This may take a moment...")
    print("Initializing Medical RAG Agent. This may take a moment...") # Also print to console

    try:
        agent_executor = create_medical_agent()
        logging.info("Medical RAG Agent initialized successfully. Type 'exit' or 'quit' to end.")
        print("Medical RAG Agent initialized successfully. Type 'exit' or 'quit' to end.")
    except Exception as e:
        error_msg = f"Failed to initialize the medical agent: {e}. Please check your LLM server connection, API configurations in .env, and that the RAG index exists at the expected location ('{PROJECT_ROOT / 'vector_store_notebook'}')."
        logging.error(error_msg, exc_info=True)
        print(f"\n[FATAL ERROR]\n{error_msg}\n")
        return # Exit the script

    # Interactive Loop
    while True:
        try:
            user_query = input("\nUser Query (type 'exit' or 'quit' to end): ")
        except KeyboardInterrupt: # Handle Ctrl+C gracefully
            print("\nExiting CLI...")
            break
            
        if user_query.lower() in ['exit', 'quit']:
            print("Exiting CLI...")
            break
        
        if not user_query.strip():
            continue

        logging.info(f"Received user query: {user_query}")

        try:
            logging.info(f"Invoking agent with input: {user_query}")
            response = agent_executor.invoke({"input": user_query})
            agent_output = response.get('output', "Agent did not produce a direct output string.")
            
            print(f"\n[AGENT RESPONSE]\n{agent_output}\n")
            logging.info(f"Agent full response for query '{user_query}': {response}")

        except Exception as e:
            error_msg = f"An error occurred: {e}"
            logging.error(f"Error during agent execution for query '{user_query}': {e}", exc_info=True)
            print(f"\n[ERROR]\n{error_msg}\nPlease check the local LLM server connection and try again.\n")
            if "Connection error" in str(e) or "refused" in str(e).lower():
                print("Hint: The error suggests a problem connecting to the LLM server. Ensure it's running and accessible.")
            elif "OPENAI_API_BASE" in str(e) or "ValueError" in str(e): # Catching common init errors if they happen mid-run
                print("Hint: The error might be related to LLM configuration (API base URL). Check your .env file and LLM server settings.")


if __name__ == '__main__':
    main()
