import os
import logging
from langchain_openai import ChatOpenAI
from typing import Optional, Dict
from pathlib import Path

# Import configuration system
from config import initialize_medical_rag_config

# Initialize configuration (this handles all path setup, logging, and env loading)
config = initialize_medical_rag_config()
logger = logging.getLogger(__name__)

def get_langchain_llm(config_override: Optional[Dict] = None) -> ChatOpenAI:
    """
    Initializes and returns a LangChain ChatOpenAI LLM instance.

    Args:
        config_override (Optional[Dict]): A dictionary to override default LLM parameters.
            Expected keys: "api_base_url", "api_key", "model_name", "temperature",
                           "max_tokens", "request_timeout".

    Returns:
        ChatOpenAI: The initialized LangChain LLM instance.

    Raises:
        ValueError: If the API base URL is not set.
    """
    # Configuration is already loaded at module level
    # Use the global config as base, then apply any overrides
    
    if config_override is None:
        config_override = {}

    # Initialize parameters with defaults from config, then override with config_override
    api_base_url = config_override.get("api_base_url", config['llm_api_base'])
    api_key = config_override.get("api_key", os.getenv("OPENAI_API_KEY", "not-needed"))
    model_name = config_override.get("model_name", config['llm_model'])
    temperature = float(config_override.get("temperature", config['llm_temperature']))
    max_tokens = int(config_override.get("max_tokens", os.getenv("LLM_MAX_TOKENS", "1024")))
    request_timeout = int(config_override.get("request_timeout", os.getenv("LLM_REQUEST_TIMEOUT", "120")))

    if not api_base_url:
        logger.error("OPENAI_API_BASE URL is not set in .env or config. Cannot initialize LLM.")
        raise ValueError("API Base URL is required but not set.")

    logger.info(f"Initializing LLM with parameters:")
    logger.info(f"  API Base URL: {api_base_url}")
    logger.info(f"  Model Name: {model_name}")
    logger.info(f"  Temperature: {temperature}")
    logger.info(f"  Max Tokens: {max_tokens}")
    logger.info(f"  Request Timeout: {request_timeout}")
    # Avoid logging API key directly for security, just confirm if it's set (e.g., "Key Used: Yes/No")
    logger.info(f"  API Key Provided: {'Yes' if api_key != 'not-needed' and api_key else 'No'}")

    llm = ChatOpenAI(
        openai_api_base=api_base_url,
        openai_api_key=api_key,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        request_timeout=request_timeout,
        # Other parameters like streaming=True could be added here or via config
    )
    
    return llm

if __name__ == '__main__':
    # Only for demonstration/testing, not for production use
    print("Attempting to initialize and test LangChain LLM service...")
    
    # Configuration is already loaded at module level
    # Example: override some parameters if needed for testing
    # test_config = {"temperature": 0.5, "model_name": "alternative-local-model"}
    # llm_instance = get_langchain_llm(config_override=test_config)
    
    try:
        llm_instance = get_langchain_llm() # Uses configuration defaults

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
                logger.error(f"Error during LLM invocation: {e}", exc_info=True)
                print("\n--- ERROR DURING LLM INVOCATION ---")
                print("Failed to get a response from the LLM.")
                print("Please ensure that your local LLM server (e.g., LM Studio, Ollama) is running,")
                print("a model is loaded/served, and the OPENAI_API_BASE in your .env file is correctly set,")
                print(f"pointing to your local server (e.g., http://localhost:1234/v1).")
                print(f"Current API Base used: {llm_instance.base_url if llm_instance else 'N/A'}")
                if "Connection error" in str(e) or "refused" in str(e).lower():
                    print("The error message suggests a connection issue. Check server status and network.")
                elif "404" in str(e) and "Not Found" in str(e):
                     print("The error message suggests the API endpoint might be incorrect or the model not found on the server.")

        else:
            # This case should ideally not be reached if get_langchain_llm raises ValueError for missing URL
            print("Failed to initialize LLM instance (get_langchain_llm returned None or failed).")

    except ValueError as ve: # Catch ValueError from get_langchain_llm if API base is missing
        logger.error(f"LLM Initialization Error: {ve}")
        print(f"\n--- ERROR DURING LLM INITIALIZATION ---")
        print(str(ve))
        print("Please ensure OPENAI_API_BASE is set in your .env file or passed in config.")
    except Exception as e_init: # Catch any other unexpected error during init
        logger.error(f"An unexpected error occurred during LLM initialization: {e_init}", exc_info=True)
        print(f"\n--- UNEXPECTED ERROR DURING LLM INITIALIZATION ---")
        print(str(e_init))

    print("\nLLM service script finished.")
