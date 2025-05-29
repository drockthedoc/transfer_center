#!/usr/bin/env python3
"""
Quick test to determine correct ChatOpenAI parameters
"""

from langchain_openai import ChatOpenAI
import inspect

try:
    # Try different parameter combinations to see what works
    print("Testing ChatOpenAI parameter names...")
    
    # Try the new style parameters
    try:
        llm = ChatOpenAI(
            openai_api_base="http://localhost:1234/v1",
            openai_api_key="test-key",
            model_name="test-model",
            temperature=0.1
        )
        print("SUCCESS: Using openai_api_base, openai_api_key, model_name")
        print(f"  API Base: {getattr(llm, 'openai_api_base', 'N/A')}")
        print(f"  Model: {getattr(llm, 'model_name', 'N/A')}")
    except Exception as e:
        print(f"FAILED with openai_api_base style: {e}")
        
        # Try the newer style parameters
        try:
            llm = ChatOpenAI(
                base_url="http://localhost:1234/v1",
                api_key="test-key", 
                model="test-model",
                temperature=0.1
            )
            print("SUCCESS: Using base_url, api_key, model")
            print(f"  Base URL: {getattr(llm, 'base_url', 'N/A')}")
            print(f"  Model: {getattr(llm, 'model', 'N/A')}")
        except Exception as e2:
            print(f"FAILED with base_url style: {e2}")
            
            # Try the original style
            try:
                llm = ChatOpenAI(
                    openai_api_base="http://localhost:1234/v1",
                    openai_api_key="test-key",
                    model="test-model",
                    temperature=0.1
                )
                print("SUCCESS: Using openai_api_base, openai_api_key, model")
                print(f"  API Base: {getattr(llm, 'openai_api_base', 'N/A')}")
                print(f"  Model: {getattr(llm, 'model', 'N/A')}")
            except Exception as e3:
                print(f"FAILED with mixed style: {e3}")
                
                # Show the actual signature
                print("\nActual ChatOpenAI signature:")
                print(inspect.signature(ChatOpenAI.__init__))

except Exception as main_e:
    print(f"Error importing or testing: {main_e}")
