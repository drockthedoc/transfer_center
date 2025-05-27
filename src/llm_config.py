from langchain_openai import ChatOpenAI

# Configuration for LM Studio
LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
LM_STUDIO_API_KEY = "not-needed"  # LM Studio does not require an API key
# Make sure this model name matches exactly what is loaded in your LM Studio
LM_STUDIO_MODEL_NAME = "LM Studio Community/Meta-Llama-3-8B-Instruct-GGUF"

def get_llm(temperature: float = 0.1):
    """Initializes and returns the LangChain ChatOpenAI model configured for LM Studio."""
    llm = ChatOpenAI(
        base_url=LM_STUDIO_BASE_URL,
        api_key=LM_STUDIO_API_KEY,
        model_name=LM_STUDIO_MODEL_NAME,
        temperature=temperature,
        # You can add other parameters like max_tokens if needed
        # model_kwargs={"top_p": 0.9}
    )
    return llm

# Example of instantiating the LLM for direct import if preferred
# default_llm = get_llm()

if __name__ == '__main__':
    # Quick test to see if the LLM can be initialized and invoked
    try:
        print(f"Attempting to initialize LLM with model: {LM_STUDIO_MODEL_NAME}")
        llm_instance = get_llm()
        print("LLM initialized successfully.")
        
        # Simple invocation test (ensure your LM Studio server is running)
        # print("\nAttempting a simple invocation...")
        # response = llm_instance.invoke("Hello, how are you?")
        # print("LLM response:", response.content)
        print("\nTo run a full invocation test, uncomment the lines above and ensure LM Studio is running.")
        print(f"Using base URL: {LM_STUDIO_BASE_URL}")

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure LM Studio is running and the model name is correct.")
