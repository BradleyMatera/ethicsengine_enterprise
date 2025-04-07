import asyncio
import json
import logging
import os
from typing import Optional

# Attempt to import LLMConfig, handle gracefully if autogen is not installed
try:
    from autogen import LLMConfig
    AUTOGEN_AVAILABLE = True
except ImportError:
    LLMConfig = None # Define as None if import fails
    AUTOGEN_AVAILABLE = False

from .settings import settings

logger = logging.getLogger(__name__)

# --- Initialize Semaphore ---
semaphore = asyncio.Semaphore(settings.max_concurrent_llm_calls)
logger.info(f"Initialized asyncio.Semaphore with limit: {settings.max_concurrent_llm_calls}")

# --- Initialize LLMConfig ---
llm_config: Optional['LLMConfig'] = None # Initialize as None
_config_list_source = "none" # Track where the config came from

if AUTOGEN_AVAILABLE and LLMConfig:
    loaded_config_list = None
    # 1. Try loading from the specific environment variable first (as an override)
    config_list_env_value = os.getenv(settings.config_list_env_var)
    if config_list_env_value:
        logger.info(f"Attempting to load LLM config from environment variable: {settings.config_list_env_var}")
        try:
            # Use LLMConfig.from_json which handles file paths or JSON strings
            _llm_config_loader = LLMConfig.from_json(env=settings.config_list_env_var)
            loaded_config_list = _llm_config_loader.config_list
            if loaded_config_list:
                _config_list_source = f"env_var ({settings.config_list_env_var})"
                logger.info(f"Successfully loaded LLM config list from '{settings.config_list_env_var}'.")
            else:
                 logger.warning(f"Env var '{settings.config_list_env_var}' set, but failed to load a valid config list from it.")
        except FileNotFoundError:
            logger.error(f"Env var '{settings.config_list_env_var}' points to a file path, but the file was not found.")
            # Continue to fallback
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from env var '{settings.config_list_env_var}'. Ensure it's valid JSON or a path to a valid JSON file.")
            # Continue to fallback
        except Exception as e:
            logger.error(f"Unexpected error loading LLM config from '{settings.config_list_env_var}': {e}", exc_info=True)
            # Continue to fallback

    # 2. If not loaded from env var, use the default config list + OPENAI_API_KEY
    if not loaded_config_list:
        logger.info("LLM config not loaded from environment variable, attempting default configuration.")
        default_list = settings.default_llm_config_list
        api_key = os.getenv("OPENAI_API_KEY")

        if not default_list:
             logger.warning("No default LLM config list defined in settings.")
        elif not api_key:
             logger.warning("OPENAI_API_KEY environment variable not set. Cannot use default LLM config.")
        else:
            # Create a new list with the API key added to each entry
            loaded_config_list = []
            for item in default_list:
                new_item = item.copy()
                new_item["api_key"] = api_key
                loaded_config_list.append(new_item)

            if loaded_config_list:
                 _config_list_source = "default + OPENAI_API_KEY"
                 logger.info(f"Using default LLM config list with API key from OPENAI_API_KEY.")
            else:
                 # This case shouldn't happen if default_list was valid, but good to handle
                 logger.error("Failed to construct LLM config from default list and API key.")


    # 3. If a valid config list was loaded (either from env var or default+key), create the LLMConfig object
    if loaded_config_list:
        try:
            # Simplify instantiation - pass only config_list
            llm_config = LLMConfig(config_list=loaded_config_list)
            # We might need to set temperature/timeout later if needed, perhaps on the agent level
            logger.info(f"Initialized global LLMConfig (Source: {_config_list_source}) with config_list only.")
            # Manually set temperature/timeout on the object if needed and available
            # if hasattr(llm_config, 'temperature'):
            #     llm_config.temperature = settings.default_llm_temperature
            # if hasattr(llm_config, 'timeout'):
            #     llm_config.timeout = settings.default_llm_timeout

        except Exception as e:
             logger.error(f"Error creating LLMConfig object from loaded list (Source: {_config_list_source}): {e}", exc_info=True)
             llm_config = None # Ensure it's None if instantiation fails
    else:
        logger.error("Failed to load any valid LLM configuration. LLM functionality will be disabled.")

else:
     if not AUTOGEN_AVAILABLE:
         logger.error("Autogen library not found. LLM functionality will be disabled.")
     # If LLMConfig is None for some other reason (shouldn't happen if AUTOGEN_AVAILABLE is True)
     elif not LLMConfig:
          logger.error("LLMConfig class could not be resolved even though Autogen seems available. LLM functionality disabled.")

# --- Initialize Concurrency Monitor ---
# Import late to avoid circular dependency if monitor imports config items
from utils.concurrency_monitor import ConcurrencyMonitor
# Pass the limit from settings during instantiation
concurrency_monitor = ConcurrencyMonitor(
    semaphore=semaphore,
    limit=settings.max_concurrent_llm_calls,
    name="LLM_Semaphore"
)


# --- Expose key configurations for easy import ---
# Make settings, semaphore, llm_config, and constants easily importable from 'config'
AGENT_TIMEOUT = settings.agent_timeout
AG2_REASONING_SPECS = settings.ag2_reasoning_specs

__all__ = [
    "settings",
    "semaphore",
    "llm_config",
    "concurrency_monitor", # Export the monitor instance
    "AGENT_TIMEOUT",
    "AG2_REASONING_SPECS",
    "AUTOGEN_AVAILABLE" # Expose availability flag
]
