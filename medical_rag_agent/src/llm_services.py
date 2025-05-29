import os
import sys
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from typing import Optional, Dict
from pathlib import Path # For __main__ block path handling

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_langchain_llm(config: Optional[Dict] = None) -> ChatOpenAI:
    """
    Initializes and returns a LangChain ChatOpenAI LLM instance.

    Args:
        config (Optional[Dict]): A dictionary to override default LLM parameters.
            Expected keys: "api_base_url", "api_key", "model_name", "temperature",
                           "max_tokens", "request_timeout".

    Returns:
        ChatOpenAI: The initialized LangChain LLM instance.
    """
    # Load environment variables from .env file in the project root
    # Assuming this script is in medical_rag_agent/src/
    project_root = Path(__file__).resolve().parent.parent
    dotenv_path = project_root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)
        logging.info(f".env file loaded from {dotenv_path}")
    else:
        logging.info(f".env file not found at {dotenv_path}. Using environment variables if available.")

    if config is None:
        config = {}

    # Initialize parameters with defaults, then override with config or .env
    api_base_url = config.get("api_base_url", os.getenv("OPENAI_API_BASE"))
    api_key = config.get("api_key", os.getenv("OPENAI_API_KEY", "not-needed"))
    model_name = config.get("model_name", os.getenv("LOCAL_MODEL_NAME", "local-medical-expert")) # Using LOCAL_MODEL_NAME from .env if available
    temperature = float(config.get("temperature", os.getenv("LLM_TEMPERATURE", 0.1)))
    max_tokens = int(config.get("max_tokens", os.getenv("LLM_MAX_TOKENS", 1024)))
    request_timeout = int(config.get("request_timeout", os.getenv("LLM_REQUEST_TIMEOUT", 120)))

    if not api_base_url:
        logging.error("OPENAI_API_BASE URL is not set in .env or config. Cannot initialize LLM.")
        # Depending on desired behavior, could raise an error or return None
        # For now, let it proceed and LangChain/OpenAI client will likely fail if it's truly needed and None
        # However, ChatOpenAI might require it.
        raise ValueError("API Base URL is required but not set.")


    logging.info(f"Initializing LLM with parameters:")
    logging.info(f"  API Base URL: {api_base_url}")
    logging.info(f"  Model Name: {model_name}")
    logging.info(f"  Temperature: {temperature}")
    logging.info(f"  Max Tokens: {max_tokens}")
    logging.info(f"  Request Timeout: {request_timeout}")
    # Avoid logging API key directly for security, just confirm if it's set (e.g., "Key Used: Yes/No")
    logging.info(f"  API Key Provided: {'Yes' if api_key != 'not-needed' and api_key else 'No'}")


    llm = ChatOpenAI(
        openai_api_base=api_base_url,
        openai_api_key=api_key,
        model=model_name, # LangChain uses 'model'
        temperature=temperature,
        max_tokens=max_tokens,
        request_timeout=request_timeout,
        # Other parameters like streaming=True could be added here or via config
    )
    
    return llm

if __name__ == '__main__':
    # No specific sys.path adjustment needed here if src is added to PYTHONPATH
    # or if this script is run as part of the package.
    # The load_dotenv within get_langchain_llm handles finding the .env from project root.

    print("Attempting to initialize and test LangChain LLM service...")
    
    # Example: override some parameters if needed for testing
    # test_config = {"temperature": 0.5, "model_name": "alternative-local-model"}
    # llm_instance = get_langchain_llm(config=test_config)
    
    try:
        llm_instance = get_langchain_llm() # Uses .env defaults or hardcoded defaults

        if llm_instance:
            print("\nLLM instance created successfully.")
            print(f"Attempting to invoke LLM (Model: {llm_instance.model_name}) at {llm_instance.openai_api_base}...")
            
            # Test invocation
            try:
                query = "Briefly explain what a Retrieval Augmented Generation (RAG) system is in one sentence."
                print(f"Sending query: \"{query}\"")
                response = llm_instance.invoke(query)
                print(f"\nLLM Response: {response.content}")
            except Exception as e: # Catching a broad exception for now
                logging.error(f"Error during LLM invocation: {e}", exc_info=True)
                print("\n--- ERROR DURING LLM INVOCATION ---")
                print("Failed to get a response from the LLM.")
                print("Please ensure that your local LLM server (e.g., LM Studio, Ollama) is running,")
                print("a model is loaded/served, and the OPENAI_API_BASE in your .env file is correctly set,")
                print(f"pointing to your local server (e.g., http://localhost:1234/v1).")
                print(f"Current API Base used: {llm_instance.openai_api_base if llm_instance else 'N/A'}")
                if "Connection error" in str(e) or "refused" in str(e).lower():
                    print("The error message suggests a connection issue. Check server status and network.")
                elif "404" in str(e) and "Not Found" in str(e):
                     print("The error message suggests the API endpoint might be incorrect or the model not found on the server.")

        else:
            # This case should ideally not be reached if get_langchain_llm raises ValueError for missing URL
            print("Failed to initialize LLM instance (get_langchain_llm returned None or failed).")

    except ValueError as ve: # Catch ValueError from get_langchain_llm if API base is missing
        logging.error(f"LLM Initialization Error: {ve}")
        print(f"\n--- ERROR DURING LLM INITIALIZATION ---")
        print(str(ve))
        print("Please ensure OPENAI_API_BASE is set in your .env file or passed in config.")
    except Exception as e_init: # Catch any other unexpected error during init
        logging.error(f"An unexpected error occurred during LLM initialization: {e_init}", exc_info=True)
        print(f"\n--- UNEXPECTED ERROR DURING LLM INITIALIZATION ---")
        print(str(e_init))

    print("\nLLM service script finished.")
