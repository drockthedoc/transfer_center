import logging
import sys
from pathlib import Path

# Add the project root to sys.path for imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

# Try to import required dependencies with fallbacks
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    logger.warning("python-dotenv not available. Environment loading will be skipped.")
    DOTENV_AVAILABLE = False
    def load_dotenv(*args, **kwargs):
        pass

try:
    from langchain_openai import ChatOpenAI
    from langchain.agents import AgentExecutor, create_openai_tools_agent
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    logger.error(f"LangChain dependencies not available: {e}")
    LANGCHAIN_AVAILABLE = False
    # Create fallback classes
    class ChatOpenAI:
        pass
    class AgentExecutor:
        pass
    def create_openai_tools_agent(*args, **kwargs):
        return None
    class ChatPromptTemplate:
        @classmethod
        def from_messages(cls, messages):
            return cls()
    class MessagesPlaceholder:
        def __init__(self, variable_name):
            self.variable_name = variable_name

# Import configuration system
try:
    from config import initialize_medical_rag_config
    config = initialize_medical_rag_config()
    PROJECT_ROOT_AGENT = config.get('paths', {}).get('project_root', project_root)
except ImportError as e:
    logger.warning(f"Could not import config: {e}. Using fallback configuration.")
    PROJECT_ROOT_AGENT = project_root
    config = {'paths': {'project_root': PROJECT_ROOT_AGENT}}

# Import modules using configured paths
try:
    from llm_services import get_langchain_llm
except ImportError:
    try:
        from medical_rag_agent.src.llm_services import get_langchain_llm
    except ImportError as e:
        logger.error(f"Failed to import get_langchain_llm: {e}")
        def get_langchain_llm():
            if LANGCHAIN_AVAILABLE:
                return ChatOpenAI(api_key="dummy", base_url="http://localhost:1234/v1")
            else:
                raise ImportError("LangChain not available")

try:
    from agent.tools import all_tools
except ImportError:
    try:
        from medical_rag_agent.src.agent.tools import all_tools
    except ImportError as e:
        logger.error(f"Failed to import all_tools: {e}")
        all_tools = []  # Fallback to empty tools list

try:
    from agent.prompts import MEDICAL_AGENT_SYSTEM_PROMPT
except ImportError:
    try:
        from medical_rag_agent.src.agent.prompts import MEDICAL_AGENT_SYSTEM_PROMPT
    except ImportError as e:
        logger.warning(f"Failed to import MEDICAL_AGENT_SYSTEM_PROMPT: {e}. Using default prompt.")
        MEDICAL_AGENT_SYSTEM_PROMPT = "You are a helpful medical assistant that can help with patient care decisions and recommendations."


def create_medical_agent():
    """
    Creates and returns a medical agent executor.
    Returns:
        AgentExecutor: The agent executor instance.
    Raises:
        Exception: If LLM or tools cannot be initialized.
    """
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("LangChain dependencies are not available. Please install them with: pip install langchain langchain-openai langchain-core")
    
    # Load .env from the project root (medical_rag_agent/)
    env_path = PROJECT_ROOT_AGENT / ".env"
    if env_path.exists() and DOTENV_AVAILABLE:
        load_dotenv(dotenv_path=env_path)
        logging.info(f"Agent: .env loaded from {env_path}")
    else:
        logging.info(f"Agent: .env file not found at {env_path} or dotenv not available. Relying on pre-loaded env vars or tool-specific loading.")

    logging.info("Initializing LLM for the agent...")
    try:
        llm = get_langchain_llm()
    except Exception as e:
        logging.error(f"Failed to initialize LLM: {e}")
        raise
    logging.info("LLM initialized.")

    logging.info("Defining agent prompt...")
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
    
    try:
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
            print(response)
            
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
            
    except ImportError as e:
        print(f"\n--- IMPORT ERROR ---")
        print(f"Missing dependencies: {e}")
        print("\nTo fix this, install the required dependencies:")
        print("cd medical_rag_agent")
        print("pip install -r requirements.txt")
        
    print("\n--- Medical Agent Test Finished ---")
