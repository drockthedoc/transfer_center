"""
LLM interaction logging module for the Transfer Center application.

This module provides specialized logging for all LLM interactions,
capturing both input prompts and output responses in timestamped log files.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class LLMLogger:
    """
    Logger for LLM interactions with detailed input/output tracking.
    
    This class handles logging of all LLM interactions to both:
    1. A standard Python logger for console/application logging
    2. A dedicated file logger for detailed input/output logging with timestamps
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize the LLM logger.
        
        Args:
            log_dir: Directory for LLM interaction log files.
                    Defaults to 'logs/llm' in the application directory.
        """
        # Set up standard Python logger
        self.logger = logging.getLogger("llm.interactions")
        
        # Create log directory if it doesn't exist
        if log_dir is None:
            # Use the specified directory structure
            self.log_dir = Path("logs/llm_interactions")
        else:
            self.log_dir = Path(log_dir)
            
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create the log file with the specified date-time stamp format
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.log_dir / f"{timestamp}_interaction.log"
        
        # Track interaction count for the session
        self.interaction_count = 0
        
        self.logger.info(f"LLM interaction logging initialized. Log file: {self.log_file}")

    def log_interaction(
        self, 
        component: str,
        method: str,
        input_data: Dict[str, Any], 
        output_data: Any,
        model: str,
        success: bool,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a complete LLM interaction with input and output.
        
        Args:
            component: The component making the request (e.g., 'EntityExtractor')
            method: The method or function making the request
            input_data: The input data/prompt sent to the LLM
            output_data: The output/response received from the LLM
            model: The model used for the interaction
            success: Whether the interaction was successful
            error: Error message if the interaction failed
            metadata: Additional metadata to log
        """
        self.interaction_count += 1
        timestamp = datetime.now().isoformat()
        
        # Create log entry
        log_entry = {
            "timestamp": timestamp,
            "interaction_id": self.interaction_count,
            "component": component,
            "method": method,
            "model": model,
            "success": success,
            "input": input_data,
            "output": output_data,
            "error": error,
        }
        
        if metadata:
            log_entry["metadata"] = metadata
            
        # Log to standard logger (minimal info)
        status = "SUCCESS" if success else f"FAILED: {error}"
        self.logger.info(
            f"LLM Interaction #{self.interaction_count} | Component: {component}.{method} | Model: {model} | Status: {status}"
        )
        
        # Log detailed information to file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{json.dumps(log_entry, indent=2, default=str)}\n")
                f.write("---\n")  # Separator between entries
        except Exception as e:
            self.logger.error(f"Failed to write to LLM log file: {e}")
    
    def log_prompt(
        self,
        component: str,
        method: str,
        prompt: str,
        model: str,
        messages: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log just the prompt being sent to the LLM (before getting a response).
        
        Args:
            component: The component making the request
            method: The method or function making the request
            prompt: The text prompt being sent
            model: The model being used
            messages: Optional formatted messages list for chat completions
            metadata: Additional metadata to log
        """
        self.interaction_count += 1
        timestamp = datetime.now().isoformat()
        
        # Create log entry
        log_entry = {
            "timestamp": timestamp,
            "interaction_id": self.interaction_count,
            "component": component,
            "method": method,
            "model": model,
            "prompt": prompt,
            "messages": messages,
            "type": "prompt_only"
        }
        
        if metadata:
            log_entry["metadata"] = metadata
            
        # Log to standard logger
        self.logger.info(
            f"LLM Prompt #{self.interaction_count} | Component: {component}.{method} | Model: {model}"
        )
        self.logger.debug(f"Prompt content: {prompt[:100]}...")
        
        # Log to file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{json.dumps(log_entry, indent=2, default=str)}\n")
                f.write("---\n")  # Separator between entries
        except Exception as e:
            self.logger.error(f"Failed to write to LLM log file: {e}")
            
        # Return the interaction ID for potential follow-up with response
        return self.interaction_count
        
    def log_response(
        self,
        interaction_id: int,
        output_data: Any,
        success: bool,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log the response from an LLM interaction (follow-up to log_prompt).
        
        Args:
            interaction_id: The ID returned from log_prompt
            output_data: The output/response received from the LLM
            success: Whether the interaction was successful
            error: Error message if the interaction failed
            metadata: Additional metadata to log
        """
        timestamp = datetime.now().isoformat()
        
        # Create log entry
        log_entry = {
            "timestamp": timestamp,
            "interaction_id": interaction_id,
            "type": "response_only",
            "success": success,
            "output": output_data,
            "error": error,
        }
        
        if metadata:
            log_entry["metadata"] = metadata
            
        # Log to standard logger
        status = "SUCCESS" if success else f"FAILED: {error}"
        self.logger.info(
            f"LLM Response #{interaction_id} | Status: {status}"
        )
        
        # Log to file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{json.dumps(log_entry, indent=2, default=str)}\n")
                f.write("---\n")  # Separator between entries
        except Exception as e:
            self.logger.error(f"Failed to write to LLM log file: {e}")


# Create a singleton instance for global use
llm_logger = LLMLogger()


def get_llm_logger() -> LLMLogger:
    """
    Get the global LLM logger instance.
    
    Returns:
        The singleton LLMLogger instance
    """
    return llm_logger
