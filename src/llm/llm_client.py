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

        response = requests.post(url, headers=self.config["headers"], json=payload)

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
            raise Exception(f"OpenAI API error: {response.status_code}")

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

        response = requests.post(url, headers=self.config["headers"], json=payload)

        if response.status_code == 200:
            return response.json()["content"][0]["text"]
        else:
            logger.error(
                f"Anthropic API error: {response.status_code} - {response.text}"
            )
            raise Exception(f"Anthropic API error: {response.status_code}")


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
