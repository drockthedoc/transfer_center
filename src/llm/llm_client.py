"""
LLM Client Module

This module provides a client interface for making calls to the LLM API.
It handles authentication, request formatting, and error handling.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the structured LLM interaction logger
from src.llm.llm_logging import get_llm_logger


class LLMClient:
    """
    Client for making calls to LLM APIs.
    Supports multiple providers with fallback mechanisms.
    """

    def __init__(self, provider: str = "openai", api_key: Optional[str] = None):
        """
        Initialize the LLM client.

        Args:
            provider: The LLM provider to use (default: "openai")
            api_key: API key for the provider (default: None, will try to get from environment)
        """
        self.provider = provider
        self.api_key = api_key or os.environ.get(f"{provider.upper()}_API_KEY")
        self.interaction_logger = get_llm_logger() # Get the structured logger

        if not self.api_key:
            logger.warning(
                f"No API key provided for {provider}. Some functions may not work."
            )

        # Configure base URLs and models based on provider
        self.config = self._get_provider_config(provider)

    def _get_provider_config(self, provider: str) -> Dict[str, Any]:
        """
        Get configuration for the specified provider.

        Args:
            provider: LLM provider name

        Returns:
            Provider configuration
        """
        configs = {
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            },
            "anthropic": {
                "base_url": "https://api.anthropic.com/v1",
                "model": "claude-3-opus-20240229",
                "headers": {
                    "Content-Type": "application/json",
                    "x-api-key": f"{self.api_key}",
                    "anthropic-version": "2023-06-01",
                },
            },
            # Add other providers as needed
        }

        return configs.get(provider.lower(), configs["openai"])

    def generate(
        self, prompt: str, max_tokens: int = 2000, temperature: float = 0.0
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for response generation (0.0 = deterministic)

        Returns:
            LLM response as a string
        """
        try:
            if self.provider == "openai":
                return self._generate_openai(prompt, max_tokens, temperature)
            elif self.provider == "anthropic":
                return self._generate_anthropic(prompt, max_tokens, temperature)
            else:
                logger.warning(
                    f"Unsupported provider: {self.provider}. Falling back to OpenAI."
                )
                return self._generate_openai(prompt, max_tokens, temperature)
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            # Attempt fallback to an alternative provider
            if self.provider != "openai":
                logger.info("Attempting fallback to OpenAI")
                old_provider = self.provider
                self.provider = "openai"
                self.config = self._get_provider_config("openai")
                try:
                    response = self._generate_openai(prompt, max_tokens, temperature)
                    logger.info(f"Fallback to OpenAI successful")
                    # Reset to original provider for next call
                    self.provider = old_provider
                    self.config = self._get_provider_config(old_provider)
                    return response
                except Exception as fallback_e:
                    logger.error(f"Fallback to OpenAI also failed: {fallback_e}")
                    # Reset to original provider for next call
                    self.provider = old_provider
                    self.config = self._get_provider_config(old_provider)

            # If all attempts fail, return an error message
            return "ERROR: Unable to generate LLM response due to API issues."

    def _generate_openai(
        self, prompt: str, max_tokens: int = 2000, temperature: float = 0.0
    ) -> str:
        """
        Generate a response using the OpenAI API.

        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for response generation

        Returns:
            LLM response as a string
        """
        url = f"{self.config['base_url']}/chat/completions"

        payload = {
            "model": self.config["model"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        response_content = None
        error_message = None
        success = False
        
        try:
            response = requests.post(url, headers=self.config["headers"], json=payload)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
            response_content = response.json()["choices"][0]["message"]["content"]
            success = True
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API request failed: {e}")
            error_message = str(e)
            raise  # Re-raise the exception to be handled by the calling method
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse OpenAI response: {e}. Response: {response.text[:200]}")
            error_message = f"Failed to parse OpenAI response: {e}"
            raise Exception(error_message) # Re-raise as a generic exception
        finally:
            self.interaction_logger.log_interaction(
                component="LLMClient",
                method="_generate_openai",
                input_data={"prompt": prompt, "payload": payload}, # Log the original prompt and the full payload
                output_data=response_content if success else None,
                model=self.config["model"],
                success=success,
                error=error_message,
                metadata={"provider": "openai", "status_code": response.status_code if 'response' in locals() else None}
            )
        return response_content

    def _generate_anthropic(
        self, prompt: str, max_tokens: int = 2000, temperature: float = 0.0
    ) -> str:
        """
        Generate a response using the Anthropic API.

        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for response generation

        Returns:
            LLM response as a string
        """
        url = f"{self.config['base_url']}/messages"

        payload = {
            "model": self.config["model"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        response_content = None
        error_message = None
        success = False

        try:
            response = requests.post(url, headers=self.config["headers"], json=payload)
            response.raise_for_status()
            response_content = response.json()["content"][0]["text"]
            success = True
        except requests.exceptions.RequestException as e:
            logger.error(f"Anthropic API request failed: {e}")
            error_message = str(e)
            raise
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse Anthropic response: {e}. Response: {response.text[:200]}")
            error_message = f"Failed to parse Anthropic response: {e}"
            raise Exception(error_message)
        finally:
            self.interaction_logger.log_interaction(
                component="LLMClient",
                method="_generate_anthropic",
                input_data={"prompt": prompt, "payload": payload},
                output_data=response_content if success else None,
                model=self.config["model"],
                success=success,
                error=error_message,
                metadata={"provider": "anthropic", "status_code": response.status_code if 'response' in locals() else None}
            )
        return response_content


def get_llm_client(provider: str = None) -> LLMClient:
    """
    Factory function to get an LLM client instance.

    Args:
        provider: LLM provider to use (default: from environment or "openai")

    Returns:
        LLMClient instance
    """
    # Use environment variable if provider is not specified
    if not provider:
        provider = os.environ.get("LLM_PROVIDER", "openai")

    return LLMClient(provider)
