import sys
import logging
from pathlib import Path

# Add the project root to sys.path to import config
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import configuration system
from src.config import initialize_medical_rag_config

def main():
    """
    CLI entrypoint for running the Medical RAG Agent interactively.
    Uses centralized configuration management.
    """
    # Initialize configuration (this handles all path setup, logging, and env loading)
    config = initialize_medical_rag_config()
    logger = logging.getLogger(__name__)
    
    # Now import create_medical_agent using the configured paths
    try:
        from src.agent.agent import create_medical_agent
    except ImportError as e:
        logger.error(f"Failed to import create_medical_agent: {e}. Ensure the 'src' directory and its contents are structured correctly.")
        print(f"[FATAL ERROR] Could not import necessary modules. Please check project structure. Error: {e}")
        return

    logger.info("Initializing Medical RAG Agent. This may take a moment...")

    try:
        agent_executor = create_medical_agent()
        logging.info("Medical RAG Agent initialized successfully. Type 'exit' or 'quit' to end.")
    except Exception as e:
        error_msg = (
            f"Failed to initialize the medical agent: {e}. "
            f"Please check your LLM server connection, API configurations in .env, "
            f"and that the RAG index exists at the expected location."
        )
        logging.error(error_msg, exc_info=True)
        return

    # Interactive Loop
    logging.info("Starting interactive loop...")
    while True:
        try:
            user_query = input("\nUser Query (type 'exit' or 'quit' to end): ")
        except KeyboardInterrupt:
            logging.info("Received keyboard interrupt, exiting CLI...")
            break
            
        if user_query.lower() in ['exit', 'quit']:
            logging.info("User requested exit, closing CLI...")
            break
        
        if not user_query.strip():
            continue

        logging.info(f"Processing user query: {user_query}")

        try:
            response = agent_executor.invoke({"input": user_query})
            agent_output = response.get('output', "Agent did not produce a direct output string.")
            
            print(f"\n[AGENT RESPONSE]\n{agent_output}\n")
            logging.debug(f"Agent full response: {response}")

        except Exception as e:
            error_msg = f"An error occurred during agent execution: {e}"
            logging.error(f"Error for query '{user_query}': {e}", exc_info=True)
            print(f"\n[ERROR]\n{error_msg}\nPlease check the local LLM server connection and try again.\n")
            
            # Provide specific hints based on error type
            if "Connection error" in str(e) or "refused" in str(e).lower():
                logging.warning("Connection error detected - LLM server may be down")
                print("Hint: The error suggests a problem connecting to the LLM server. Ensure it's running and accessible.")
            elif "OPENAI_API_BASE" in str(e) or "ValueError" in str(e):
                logging.warning("Configuration error detected - check API settings")
                print("Hint: The error might be related to LLM configuration (API base URL). Check your .env file and LLM server settings.")


if __name__ == '__main__':
    main()
