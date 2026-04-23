import json
import tempfile
import unittest
from pathlib import Path

from api.llm_config_manager import load_llm_config


class LLMConfigManagerTests(unittest.TestCase):
    def test_load_llm_config_merges_model_and_prompt_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            config_path = temp_path / "llm_config.json"
            prompts_path = temp_path / "llm_prompts.json"

            config_path.write_text(
                json.dumps(
                    {
                        "model_type": "demo",
                        "models": {
                            "demo": {
                                "name": "demo-model",
                                "provider": "groq",
                                "description": "demo",
                                "parameters": {"max_tokens": 123, "temperature": 0.3},
                            }
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            prompts_path.write_text(
                json.dumps(
                    {
                        "state_based": "state {context}",
                        "chat_based": "chat {conversation_history} {player_message} {context}",
                        "action_based": "action {conversation_history} {player_message} {context}",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            config = load_llm_config(config_path, prompts_path)

        self.assertEqual(config.model_type, "demo")
        self.assertEqual(config.get_model_name(), "demo-model")
        self.assertEqual(config.get_chat_prompt_template(), "chat {conversation_history} {player_message} {context}")
