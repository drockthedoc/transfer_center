"""
Configuration management for the Medical RAG Agent.

This module provides centralized configuration management including:
- Path resolution and sys.path setup
- Environment variable loading
- Logging configuration
- Model and service configurations

This eliminates the need for repeated sys.path manipulation across modules.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv


def setup_paths() -> Dict[str, Path]:
    """
    Set up and configure all necessary paths for the medical RAG agent.
    
    Returns:
        Dict containing all important paths for the project.
    """
    # Determine the project structure
    current_file = Path(__file__).resolve()
    src_dir = current_file.parent  # medical_rag_agent/src/
    project_root = src_dir.parent  # medical_rag_agent/
    
    paths = {
        'project_root': project_root,
        'src_dir': src_dir,
        'data_dir': project_root / 'data',
        'scripts_dir': project_root / 'scripts',
        'vector_store_dir': project_root / 'vector_store_notebook',
        'notebooks_dir': project_root / 'notebooks',
    }
    
    # Add necessary paths to sys.path if not already present
    paths_to_add = [str(project_root), str(src_dir)]
    for path_str in paths_to_add:
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
    
    return paths


def setup_logging(level: str = "INFO", format_string: Optional[str] = None) -> None:
    """
    Configure logging for the medical RAG agent.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string for log messages
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        force=True  # Override any existing configuration
    )


def load_environment(env_file: Optional[Path] = None) -> bool:
    """
    Load environment variables from .env file.
    
    Args:
        env_file: Path to .env file. If None, will search for .env in project root.
        
    Returns:
        True if .env file was found and loaded, False otherwise.
    """
    if env_file is None:
        paths = setup_paths()
        env_file = paths['project_root'] / '.env'
    
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
        logging.info(f"Environment loaded from {env_file}")
        return True
    else:
        logging.info(f"No .env file found at {env_file}. Using system environment variables.")
        return False


def get_config() -> Dict[str, Any]:
    """
    Get consolidated configuration for the medical RAG agent.
    
    Returns:
        Dictionary containing all configuration values.
    """
    paths = setup_paths()
    
    config = {
        'paths': paths,
        'embedding_model': os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
        'llm_api_base': os.getenv('OPENAI_API_BASE', 'http://localhost:1234/v1'),
        'llm_model': os.getenv('MODEL_NAME', 'local-model'),
        'llm_temperature': float(os.getenv('TEMPERATURE', '0.1')),
        'vector_store_path': str(paths['vector_store_dir']),
        'chunk_size': int(os.getenv('CHUNK_SIZE', '1024')),
        'chunk_overlap': int(os.getenv('CHUNK_OVERLAP', '200')),
        'max_chars_per_section': int(os.getenv('MAX_CHARS_PER_SECTION', '4000')),
    }
    
    return config


def initialize_medical_rag_config(log_level: str = "INFO") -> Dict[str, Any]:
    """
    Initialize complete configuration for medical RAG agent.
    
    This is the main entry point that should be called by scripts and modules
    to set up the environment properly.
    
    Args:
        log_level: Logging level to use
        
    Returns:
        Complete configuration dictionary
    """
    # Setup logging first
    setup_logging(level=log_level)
    
    # Setup paths and load environment
    load_environment()
    
    # Get full configuration
    config = get_config()
    
    logging.info("Medical RAG Agent configuration initialized successfully")
    logging.debug(f"Configuration: {config}")
    
    return config
