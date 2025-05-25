"""
LLM Client Module

This module provides a client interface for making calls to the LLM API.
It handles authentication, request formatting, and error handling.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests

# Assuming LLMInteractionLogger is correctly defined elsewhere and imported if necessary
# from src.llm.interaction_logger import LLMInteractionLogger # Or actual path
# For now, let's use a placeholder if it's not critical for this refactor step
class LLMInteractionLogger:
    def log_interaction(self, **kwargs):
        # Placeholder implementation
        logger.debug(f"LLM Interaction: {kwargs}")

logger = logging.getLogger(__name__)

class LLMClient:
    """Client to interact with different LLM providers, configured via llm_config.json."""

    def __init__(self, provider_name: str):
        """Initialize the LLM client for a specific provider."""
        self.provider_name = provider_name
        self.interaction_logger = LLMInteractionLogger() # Replace with actual logger if available
        self.api_key: Optional[str] = None
        self.api_url: Optional[str] = None
        self.model: Optional[str] = None
        self.headers: Dict[str, str] = {}

        self._load_config()

    def _load_config(self):
        """Loads configuration for the specified provider from llm_config.json."""
        try:
            # Path from src/llm/llm_client.py to project_root/config/llm_config.json
            config_path = Path(__file__).resolve().parent.parent.parent / "config" / "llm_config.json"
            logger.info(f"Attempting to load LLM config from: {config_path}")

            if not config_path.exists():
                logger.error(f"LLM configuration file not found at {config_path}")
                raise ValueError(f"LLM configuration file not found: {config_path}")

            with open(config_path, "r") as f:
                all_configs = json.load(f)
            
            provider_config = all_configs.get(self.provider_name)

            if not provider_config:
                logger.error(f"Configuration for provider '{self.provider_name}' not found in {config_path}")
                raise ValueError(f"No config for provider '{self.provider_name}'")

            self.api_key = provider_config.get("api_key")
            self.api_url = provider_config.get("api_url")
            self.model = provider_config.get("model")

            if not self.api_url or not self.model:
                logger.error(
                    f"'api_url' or 'model' missing in config for provider '{self.provider_name}'. "
                    f"API Key is optional for local LLMs like LM Studio but URL and model are required."
                )
                raise ValueError(f"Incomplete config for '{self.provider_name}' (missing api_url or model)")
            
            self.headers = {
                "Content-Type": "application/json",
            }
            # LM Studio's OpenAI-compatible endpoint might not require an API key, 
            # or accept any string. If an API key is provided in config, include it.
            if self.api_key:
                 self.headers["Authorization"] = f"Bearer {self.api_key}"

            logger.info(f"LLMClient configured for provider '{self.provider_name}' with model '{self.model}' at URL '{self.api_url}'.")

        except FileNotFoundError:
            logger.exception(f"LLM config file not found during _load_config.")
            raise
        except json.JSONDecodeError:
            logger.exception(f"Error decoding LLM config JSON during _load_config.")
            raise
        except ValueError as ve:
            logger.error(f"Configuration error for LLMClient: {ve}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error loading LLM config: {e}")
            raise

    def generate(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.2
    ) -> str:
        """Generate a response from the configured LLM provider."""
        if not self.api_url or not self.model:
            # This case should ideally be caught by __init__, but as a safeguard:
            logger.error("LLMClient is not properly configured (missing API URL or model). Cannot generate.")
            raise ConnectionError("LLMClient not configured.")

        # Currently, we assume an OpenAI-compatible API (like LM Studio)
        # If other providers were to be truly supported, this would need a switch
        if self.provider_name == "openai" or True: # Defaulting to OpenAI-like structure
            return self._generate_openai_compatible(prompt, max_tokens, temperature)
        else:
            logger.error(f"Provider '{self.provider_name}' not supported by this client's generate method.")
            raise NotImplementedError(f"Generation for provider '{self.provider_name}' is not implemented.")

    def _generate_openai_compatible(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> str:
        """Generates a response using an OpenAI-compatible API (e.g., LM Studio)."""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "response_format": { "type": "json_object" }, # Instruct LLM to output JSON
            # "stream": False, # Explicitly not streaming for now
        }

        logger.info(f"Sending request to LLM ({self.model}) at {self.api_url} with prompt: {prompt[:100]}...")
        
        interaction_data = {
            "component": "LLMClient",
            "method": "_generate_openai_compatible",
            "input_data": {"prompt": prompt, "payload": payload},
            "model": self.model,
            "provider": self.provider_name,
            "url": self.api_url
        }

        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=60) # 60s timeout
            response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
            
            response_json = response.json()
            
            if not response_json.get("choices") or not response_json["choices"][0].get("message") or not response_json["choices"][0]["message"].get("content"):
                logger.error(f"Invalid LLM response structure: {response_json}")
                raise ValueError("LLM response missing expected 'choices[0].message.content' structure.")
            
            content = response_json["choices"][0]["message"]["content"]
            logger.info(f"LLM ({self.model}) generated response successfully.")
            self.interaction_logger.log_interaction(
                **interaction_data,
                output_data=content,
                success=True,
                status_code=response.status_code
            )
            return content

        except requests.exceptions.Timeout as e:
            logger.error(f"LLM request timed out to {self.api_url}: {e}")
            self.interaction_logger.log_interaction(**interaction_data, success=False, error=str(e), status_code=None)
            raise ConnectionError(f"LLM request timed out: {e}") from e
        except requests.exceptions.RequestException as e:
            status_code = e.response.status_code if e.response is not None else "N/A"
            response_text = e.response.text if e.response is not None else "No response text"
            logger.error(f"LLM API request failed to {self.api_url}. Status: {status_code}. Error: {e}. Response: {response_text[:200]}")
            self.interaction_logger.log_interaction(**interaction_data, success=False, error=str(e), status_code=status_code)
            raise ConnectionError(f"LLM API request failed: {e}") from e
        except (ValueError, KeyError) as e: # For JSON parsing or structure issues
            logger.error(f"Error processing LLM response: {e}. Response text: {response.text[:200] if 'response' in locals() else 'N/A'}")
            self.interaction_logger.log_interaction(**interaction_data, success=False, error=str(e), status_code=response.status_code if 'response' in locals() else None)
            raise ValueError(f"Error processing LLM response: {e}") from e

def get_llm_client(provider_name: Optional[str] = None) -> LLMClient:
    """
    Factory function to get an LLM client instance.
    If provider_name is None, it attempts to use LLM_PROVIDER env var, defaulting to 'openai'.
    """
    if provider_name is None:
        provider_name = os.environ.get("LLM_PROVIDER", "openai")
    
    logger.info(f"Attempting to get LLM client for provider: {provider_name}")
    try:
        return LLMClient(provider_name=provider_name)
    except Exception as e:
        logger.exception(f"Failed to initialize LLMClient for provider '{provider_name}'. Error: {e}")
        # Depending on desired behavior, could return a NoOpLLMClient or raise
        raise RuntimeError(f"Could not create LLM client for '{provider_name}'. Ensure 'config/llm_config.json' is correct.") from e
