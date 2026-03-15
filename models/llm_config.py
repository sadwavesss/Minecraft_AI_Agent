from pydantic import BaseModel
from typing import Dict, Any, Optional


class ModelConfig(BaseModel):
    """Configuration for a single LLM model."""
    name: str
    provider: str
    description: str = ""
    parameters: Dict[str, Any]  # Model-specific parameters (flexible)


class PromptsConfig(BaseModel):
    """Prompt templates for different scenarios."""
    state_based: str
    chat_based: str


class LLMConfig(BaseModel):
    """Main LLM configuration."""
    model_type: str  # 'qwen' or 'llama'
    models: Dict[str, ModelConfig]
    prompts: PromptsConfig

    def get_active_model(self) -> ModelConfig:
        """Get the currently active model configuration."""
        if self.model_type not in self.models:
            raise ValueError(f"Unknown model type: {self.model_type}")
        return self.models[self.model_type]

    def get_model_name(self) -> str:
        """Get the name of the active model."""
        return self.get_active_model().name

    def get_parameter(self, param_name: str, default=None) -> Any:
        """Get a specific parameter from the active model."""
        model = self.get_active_model()
        return model.parameters.get(param_name, default)

    def get_parameters(self) -> Dict[str, Any]:
        """Get all parameters for the active model."""
        return self.get_active_model().parameters.copy()

    def has_parameter(self, param_name: str) -> bool:
        """Check if a parameter exists in the active model."""
        model = self.get_active_model()
        return param_name in model.parameters

    def get_state_prompt_template(self) -> str:
        """Get the state-based prompt template."""
        return self.prompts.state_based

    def get_chat_prompt_template(self) -> str:
        """Get the chat-based prompt template."""
        return self.prompts.chat_based

