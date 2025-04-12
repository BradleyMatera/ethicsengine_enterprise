import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List # Added List
from pydantic import Field
from pydantic_settings import BaseSettings
from open_llm.config_llm import LLMSetter
# Load environment variables from a .env file if it exists
load_dotenv()

llm_setter = LLMSetter()

class Settings(BaseSettings):
    """Application settings."""

    # --- LLM Configuration & Concurrency ---
    config_list_env_var: str = Field(
        "ETHICSENGINE_CONFIG_LIST",
        validation_alias='CONFIG_LIST_ENV_VAR',
        description="Optional environment variable containing a JSON config list for LLMs, overriding the default."
    )
    # Define a default config list using a standard model
    default_llm_config_list: List[Dict[str, Any]] = Field(
        llm_setter.get_config(),
        
    )
    max_concurrent_llm_calls: int = Field(
        10,
        validation_alias='MAX_CONCURRENT_LLM_CALLS',
        description="Maximum number of concurrent calls to the LLM API."
    )
    agent_timeout: int = Field(
        600, # Increased timeout to 10 minutes
        validation_alias='AGENT_TIMEOUT',
        description="Timeout in seconds for agent stage execution (e.g., waiting for LLM response)."
    )
    default_llm_temperature: float = Field(
        0.7,
        validation_alias='DEFAULT_LLM_TEMPERATURE',
        description="Default temperature for LLM calls."
    )
    default_llm_timeout: int = Field(
        300,
        validation_alias='DEFAULT_LLM_TIMEOUT',
        description="Default timeout in seconds for underlying LLM HTTP client requests."
    )
    ag2_reasoning_specs: Dict[str, Dict[str, Any]] = Field(
        default={
            "low": {"max_depth": 1, "temperature": 0.7},
            "medium": {"max_depth": 2, "temperature": 0.5},
            "high": {"max_depth": 3, "temperature": 0.3},
            "basic": {"max_depth": 0, "temperature": 0.7} # Reverted temp for basic calls
        },
        validation_alias='AG2_REASONING_SPECS',
        description="Configuration specs for different AG2 reasoning levels (max_depth, temperature)."
    )

    # --- Paths ---
    data_dir: str = Field("data", description="Directory containing configuration files (identities, pipelines, etc.)")
    results_dir: str = Field("results", description="Directory to store pipeline run results.")
    log_dir: str = Field("logs", description="Directory for log files.")
    log_level: str = Field("INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).")

    # Add other global settings as needed

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra fields from environment

# Instantiate settings
settings = Settings()

# Ensure necessary directories exist (optional, can be done at runtime)
# os.makedirs(settings.data_dir, exist_ok=True)
# os.makedirs(settings.results_dir, exist_ok=True)
# os.makedirs(settings.log_dir, exist_ok=True)
