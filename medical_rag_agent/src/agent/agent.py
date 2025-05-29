import logging
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Import configuration system  
from config import initialize_medical_rag_config

# Initialize configuration
config = initialize_medical_rag_config()
logger = logging.getLogger(__name__)

# Import modules using configured paths
try:
    from medical_rag_agent.src.llm_services import get_langchain_llm
    from medical_rag_agent.src.agent.tools import all_tools
    from medical_rag_agent.src.agent.prompts import MEDICAL_AGENT_SYSTEM_PROMPT
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    # Try alternative import paths
    try:
        from llm_services import get_langchain_llm
        from agent.tools import all_tools
        from agent.prompts import MEDICAL_AGENT_SYSTEM_PROMPT
    except ImportError as e2:
        logger.error(f"Alternative imports also failed: {e2}")
        raise ImportError(f"Could not import required modules: {e}, {e2}")


def create_medical_agent() -> AgentExecutor:
    """
    Creates and returns a medical agent executor.
    Returns:
        AgentExecutor: The agent executor instance.
    Raises:
        Exception: If LLM or tools cannot be initialized.
    """
    # Load .env from the project root (medical_rag_agent/)
    # get_langchain_llm also does this, but good practice to ensure it's loaded early
    # if other configurations depend on it directly here.
    env_path = PROJECT_ROOT_AGENT / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logging.info(f"Agent: .env loaded from {env_path}")
    else:
        logging.info(f"Agent: .env file not found at {env_path}. Relying on pre-loaded env vars or tool-specific loading.")

    logging.info("Initializing LLM for the agent...")
    try:
        llm = get_langchain_llm() # This function already handles .env loading and defaults
    except Exception as e:
        logging.error(f"Failed to initialize LLM: {e}")
        raise
    logging.info("LLM initialized.")

    logging.info("Defining agent prompt...")
    # Ensure MEDICAL_AGENT_SYSTEM_PROMPT is correctly formatted for from_messages if it's just a string.
    # It should be a tuple like ("system", MEDICAL_AGENT_SYSTEM_PROMPT)
    prompt = ChatPromptTemplate.from_messages([
        ("system", MEDICAL_AGENT_SYSTEM_PROMPT),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    logging.info("Agent prompt defined.")

    logging.info("Creating OpenAI tools agent...")
    agent = create_openai_tools_agent(llm, all_tools, prompt)
    logging.info("OpenAI tools agent created.")

    logging.info("Creating AgentExecutor...")
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=all_tools, 
        verbose=True, 
        handle_parsing_errors=True
    )
    logging.info("AgentExecutor created.")
    
    return agent_executor

if __name__ == '__main__':
    # Only for demonstration/testing, not for production use
    print("--- Medical Agent Test ---")
    
    medical_agent_executor = create_medical_agent()
    print("Medical agent executor created.")

    test_query = (
        "Patient: 62 y/o female presenting with acute ischemic stroke symptoms, onset 2 hours ago. "
        "Needs urgent thrombectomy. Currently at Community General Hospital. "
        "Find the nearest comprehensive stroke center that can accept her."
    )
    print(f"\nTest Query: {test_query}")

    try:
        logging.info(f"Invoking agent with test query...")
        response = medical_agent_executor.invoke({"input": test_query})
        
        logging.info(f"Agent Full Response: {response}")
        print(f"\n--- Agent Full Response ---")
        print(response) # Print the whole dictionary for inspection
        
        agent_output = response.get('output')
        if agent_output:
            print(f"\n--- Agent Output (parsed) ---")
            print(agent_output)
        else:
            print("\n--- Agent did not produce a direct 'output' field. ---")
            print("This might happen if the final response structure is different or an error occurred.")

    except Exception as e:
        logging.error(f"Error during agent invocation: {e}", exc_info=True)
        print("\n--- ERROR DURING AGENT INVOCATION ---")
        print(f"An error occurred: {e}")
        print("Troubleshooting tips:")
        print("1. Local LLM Server: Ensure your local LLM server (e.g., LM Studio, Ollama) is running.")
        print("2. Model Loaded: Make sure a compatible model is loaded and served by the LLM server.")
        print("3. .env Configuration: Verify OPENAI_API_BASE in your .env file points to the correct local server address (e.g., http://localhost:1234/v1).")
        print("4. RAG Index: Ensure the RAG index exists at 'medical_rag_agent/vector_store_notebook/' and was built by the notebook.")
        print("5. Tool Functionality: Check for errors from any of the agent's tools in the verbose output above.")
        if "Connection error" in str(e) or "refused" in str(e).lower():
            print("   Specific Error Hint: The error message suggests a connection issue. Double-check server status and network accessibility.")
        elif "404" in str(e) and "Not Found" in str(e):
             print("   Specific Error Hint: The error message suggests the API endpoint might be incorrect or the model not found on the server.")
        
    print("\n--- Medical Agent Test Finished ---")
