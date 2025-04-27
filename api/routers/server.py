from fastapi import APIRouter, Depends, Request, HTTPException, status, Body
import logging
from pathlib import Path
import sys
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import requests
import json

# Add project root to path if not already added
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.concurrency_monitor import ConcurrencyMonitor # Assuming singleton or accessible instance
from open_llm.config_llm import LLMSetter
from config import llm_config

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/server",
    tags=["server"],
    responses={404: {"description": "Not found"}},
)

# Define the models for configuration
class OllamaConfig(BaseModel):
    base_url: str
    model: str

class OllamaModelInfo(BaseModel):
    name: str
    modified_at: Optional[str] = None
    size: Optional[int] = None
    digest: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class OllamaModelsResponse(BaseModel):
    models: List[OllamaModelInfo]
    is_running: bool = True

# --- Dependency to get the shared ConcurrencyMonitor instance ---
async def get_concurrency_monitor(request: Request) -> ConcurrencyMonitor:
    """
    Dependency function to retrieve the ConcurrencyMonitor instance
    stored in the application state.
    """
    if hasattr(request.app.state, 'concurrency_monitor'):
        return request.app.state.concurrency_monitor
    else:
        # This should not happen if main.py initializes it correctly
        logger.error("ConcurrencyMonitor not found in application state!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: Concurrency monitor not initialized."
        )

# --- Endpoints ---

@router.get("/check-ollama", response_model=OllamaModelsResponse)
async def check_ollama(base_url: str):
    """
    Checks if Ollama is running at the specified base URL and returns the list of available models.
    """
    try:
        # Normalize the base URL
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        
        # Extract the base part without /v1 if present
        if base_url.endswith('/v1'):
            base_url = base_url[:-3]
        
        # Make a request to the Ollama API to list available models
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            models = []
            
            # Parse the response to extract model information
            for model_data in data.get("models", []):
                model_info = OllamaModelInfo(
                    name=model_data.get("name", ""),
                    modified_at=model_data.get("modified_at", ""),
                    size=model_data.get("size", 0),
                    digest=model_data.get("digest", ""),
                    details=model_data.get("details", {})
                )
                models.append(model_info)
            
            return OllamaModelsResponse(models=models, is_running=True)
        else:
            logger.error(f"Failed to get Ollama models: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Ollama API returned error: {response.status_code} - {response.text}"
            )
    except requests.exceptions.ConnectionError:
        logger.error(f"Could not connect to Ollama at {base_url}")
        return OllamaModelsResponse(models=[], is_running=False)
    except requests.exceptions.Timeout:
        logger.error(f"Connection to Ollama at {base_url} timed out")
        return OllamaModelsResponse(models=[], is_running=False)
    except Exception as e:
        logger.error(f"Error checking Ollama: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking Ollama: {str(e)}"
        )

@router.post("/set-ollama-config", response_model=Dict[str, Any])
async def set_ollama_config(
    config: OllamaConfig = Body(...),
):
    """
    Updates the Ollama configuration with the provided base URL and model.
    This endpoint allows changing the Ollama settings without restarting the server.
    First checks if Ollama is running at the specified base URL.
    """
    try:
        # Check if Ollama is running at the specified base URL
        base_url = config.base_url
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        
        # Extract the base part without /v1 if present
        api_base_url = base_url
        if base_url.endswith('/v1'):
            api_base_url = base_url[:-3]
        
        # Make a request to the Ollama API to check if it's running
        try:
            response = requests.get(f"{api_base_url}/api/tags", timeout=5)
            
            if response.status_code != 200:
                logger.error(f"Ollama not running or unreachable at {api_base_url}: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"Ollama not running or unreachable at {api_base_url}",
                    "is_running": False
                }
            
            # Check if the specified model is available
            models_data = response.json()
            available_models = [model.get("name", "") for model in models_data.get("models", [])]
            
            if config.model not in available_models:
                logger.warning(f"Model {config.model} not found in available models: {available_models}")
                # We'll still proceed with the configuration, but warn the user
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to Ollama at {api_base_url}: {str(e)}")
            return {
                "status": "error",
                "message": f"Ollama not running or unreachable at {api_base_url}: {str(e)}",
                "is_running": False
            }
        
        # Create a new LLMSetter instance
        setter = LLMSetter()
        
        # Create the configuration dictionary
        ollama_dict = {
            "api_type": "ollama",
            "base_url": config.base_url,
            "model": config.model,
            "api_key": "None"  # Ollama doesn't need an API key
        }
        
        # Update the configuration
        new_config = setter.config_llm(ollama_dict)
        
        if new_config:
            # Update the global llm_config
            # This will be used for all future LLM calls
            from config import llm_config as global_llm_config
            from autogen import LLMConfig
            
            if global_llm_config is not None:
                # Update the existing LLMConfig object
                global_llm_config.config_list = new_config
                logger.info(f"Updated global LLM configuration with Ollama model: {config.model}, base_url: {config.base_url}")
            else:
                # Create a new LLMConfig object if it doesn't exist
                try:
                    from autogen import LLMConfig
                    import config
                    config.llm_config = LLMConfig(config_list=new_config)
                    logger.info(f"Created new global LLM configuration with Ollama model: {config.model}, base_url: {config.base_url}")
                except ImportError:
                    logger.error("Failed to import LLMConfig from autogen")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to update LLM configuration: autogen not available"
                    )
            
            return {
                "status": "success",
                "message": f"Ollama configuration updated successfully with model: {config.model}, base_url: {config.base_url}",
                "config": ollama_dict,
                "is_running": True,
                "available_models": available_models
            }
        else:
            logger.error("Failed to update Ollama configuration")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update Ollama configuration"
            )
    except Exception as e:
        logger.error(f"Error updating Ollama configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating Ollama configuration: {str(e)}"
        )

@router.get("/concurrency", response_model=dict)
async def get_server_concurrency_status(
    monitor: ConcurrencyMonitor = Depends(get_concurrency_monitor)
):
    """
    Provides information about the current LLM call concurrency limits and usage.
    """
    limit = monitor._limit
    active = monitor._active_tasks

    # Attempt to get waiter count (similar to _log_status, acknowledging potential issues)
    waiters = 0
    if hasattr(monitor._semaphore, '_waiters') and monitor._semaphore._waiters is not None:
        try:
            waiters = len(monitor._semaphore._waiters)
        except TypeError:
            waiters = -1 # Indicate unknown waiter count
            logger.debug("Could not determine exact number of waiters for semaphore in API endpoint.")
    else:
         # If _waiters doesn't exist or is None
         waiters = 0 # Assume 0 if attribute not found

    status = {
        "limit": limit,
        "active": active,
        "waiting": waiters if waiters != -1 else "unknown" # Return 'unknown' if count failed
    }

    logger.info(f"Reporting concurrency status: {status}")
    return status
