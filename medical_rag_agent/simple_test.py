#!/usr/bin/env python3

from langchain_openai import ChatOpenAI

# Create a minimal instance to see what parameters work
try:
    # Try minimal parameters
    llm = ChatOpenAI()
    print("SUCCESS: ChatOpenAI() created with no parameters")
    print(f"Available attributes: {[attr for attr in dir(llm) if not attr.startswith('_')][:10]}")
    
    # Test with specific parameters one by one
    try:
        llm = ChatOpenAI(openai_api_base="http://localhost:1234/v1")
        print("SUCCESS: openai_api_base parameter works")
    except Exception as e:
        print(f"FAILED: openai_api_base parameter: {e}")
        
    try:
        llm = ChatOpenAI(base_url="http://localhost:1234/v1")  
        print("SUCCESS: base_url parameter works")
    except Exception as e:
        print(f"FAILED: base_url parameter: {e}")
        
    try:
        llm = ChatOpenAI(model_name="test-model")
        print("SUCCESS: model_name parameter works")
    except Exception as e:
        print(f"FAILED: model_name parameter: {e}")
        
    try:
        llm = ChatOpenAI(model="test-model")
        print("SUCCESS: model parameter works")
    except Exception as e:
        print(f"FAILED: model parameter: {e}")

except Exception as e:
    print(f"Error: {e}")
