import json
import logging
from pathlib import Path
from models.llm_config import LLMConfig

logger = logging.getLogger(__name__)

# Load LLM configuration
_llm_config_path = Path("llm_config.json")

try:
    if _llm_config_path.exists():
        config_data = json.loads(_llm_config_path.read_text(encoding="utf-8"))
        llm_config = LLMConfig(**config_data)
        logger.info(f"Loaded LLM config with model: {llm_config.model_type}")
    else:
        raise FileNotFoundError("llm_config.json not found")
except Exception as e:
    logger.error(f"Failed to load LLM config: {e}")
    raise


def get_llm_config() -> LLMConfig:
    """Get the current LLM configuration."""
    return llm_config


def set_model_type(model_type: str) -> LLMConfig:
    """Change the active model type and save to config file."""
    global llm_config
    
    if model_type not in llm_config.models:
        raise ValueError(f"Unknown model type: {model_type}. Available: {list(llm_config.models.keys())}")
    
    llm_config.model_type = model_type
    
    # Save to file
    config_data = llm_config.model_dump()
    _llm_config_path.write_text(json.dumps(config_data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    logger.info(f"Changed model to: {model_type}")
    return llm_config


def get_available_models() -> list:
    """Get list of available model types."""
    return list(llm_config.models.keys())


def get_model_info(model_type: str) -> dict:
    """Get detailed info about a specific model."""
    if model_type not in llm_config.models:
        raise ValueError(f"Unknown model type: {model_type}")
    
    model = llm_config.models[model_type]
    return {
        "name": model.name,
        "provider": model.provider,
        "max_tokens": model.max_tokens,
        "temperature": model.temperature,
        "description": model.description
    }
