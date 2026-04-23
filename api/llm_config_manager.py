import json
import logging
from pathlib import Path
from models.llm_config import LLMConfig

logger = logging.getLogger(__name__)

# Load LLM configuration
_llm_config_path = Path("llm_config.json")
_llm_prompts_path = Path("llm_prompts.json")


def load_llm_config(config_path: Path | None = None, prompts_path: Path | None = None) -> LLMConfig:
    """Load model config and prompts from separate files, then merge them."""
    effective_config_path = config_path or _llm_config_path
    effective_prompts_path = prompts_path or _llm_prompts_path

    if not effective_config_path.exists():
        raise FileNotFoundError(f"{effective_config_path} not found")
    if not effective_prompts_path.exists():
        raise FileNotFoundError(f"{effective_prompts_path} not found")

    config_data = json.loads(effective_config_path.read_text(encoding="utf-8"))
    prompts_data = json.loads(effective_prompts_path.read_text(encoding="utf-8"))
    config_data["prompts"] = prompts_data
    return LLMConfig(**config_data)

try:
    llm_config = load_llm_config()
    logger.info(f"Loaded LLM config with model: {llm_config.model_type}")
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
    config_data = llm_config.model_dump(exclude={"prompts"})
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
        "max_tokens": model.parameters.get("max_tokens"),
        "temperature": model.parameters.get("temperature"),
        "description": model.description
    }
