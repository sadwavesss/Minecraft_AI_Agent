import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api.llm_config_manager import load_llm_config, set_prompt_config
from models.llm_config import PromptsConfig


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

    def test_set_prompt_config_persists_prompts_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            prompts_path = temp_path / "llm_prompts.json"
            prompts_path.write_text(
                json.dumps(
                    {
                        "state_based": "old state",
                        "chat_based": "old chat",
                        "action_based": "old action",
                        "tool_result_based": "old tool",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            prompt_config = PromptsConfig(
                state_based="state x",
                chat_based="chat x",
                action_based="action x",
                tool_result_based="tool x",
            )

            demo_config = load_llm_config(Path("llm_config.json"), Path("llm_prompts.json"))

            with patch("api.llm_config_manager._llm_prompts_path", prompts_path), patch("api.llm_config_manager.llm_config", demo_config):
                updated = set_prompt_config(prompt_config)

            saved = json.loads(prompts_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["state_based"], "state x")
            self.assertEqual(saved["tool_result_based"], "tool x")
            self.assertEqual(updated.prompts.chat_based, "chat x")
