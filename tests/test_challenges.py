import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api import challenges
from api.player_state import apply_log_to_player_state, reset_player_state
from api.tool_service import execute_tool_call
from models.log_entry import LogEntry


class ChallengeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path_patch = patch.object(challenges, "CHALLENGE_STATE_PATH", Path(self.temp_dir.name) / "challenge_state.json")
        self.path_patch.start()
        reset_player_state()
        challenges.reset_challenge_state()

    def tearDown(self):
        challenges.reset_challenge_state()
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def test_create_kill_challenge_and_complete_from_kill_telemetry(self):
        result = execute_tool_call(
            "create_challenge",
            {
                "goal_type": "kill",
                "target_query": "зомби",
                "goal_count": 1,
                "reward_item_query": "железо",
                "reward_count": 3,
                "title": "Убей зомби",
            },
        )
        self.assertTrue(result["ok"])
        active = challenges.get_active_challenge()
        self.assertIsNotNone(active)
        self.assertEqual(active["status"], "active")
        self.assertEqual(active["goal_target_id"], "minecraft:zombie")

        apply_log_to_player_state(
            LogEntry(
                level="INFO",
                event_type="mob_kill",
                event_data={"entity_id": "minecraft:zombie", "entity_name": "Zombie", "count_delta": 1},
            )
        )
        challenges.refresh_challenge_progress()

        active = challenges.get_active_challenge()
        self.assertIsNotNone(active)
        self.assertEqual(active["progress_count"], 1)
        self.assertEqual(active["status"], "completed")
        self.assertEqual(active["goal_target_name"], "зомби")

    def test_claim_completed_collect_challenge_uses_give_command_and_clears_active(self):
        result = execute_tool_call(
            "create_challenge",
            {
                "goal_type": "collect",
                "target_query": "уголь",
                "goal_count": 2,
                "reward_item_query": "железо",
                "reward_count": 4,
            },
        )
        self.assertTrue(result["ok"])

        apply_log_to_player_state(
            LogEntry(
                level="INFO",
                event_type="inventory_snapshot",
                event_data={
                    "counts": {"minecraft:coal": 2},
                    "hotbar": [],
                    "armor": [],
                    "offhand": [],
                },
            )
        )
        challenges.refresh_challenge_progress()

        claim_result = execute_tool_call("claim_challenge_reward", {})
        self.assertTrue(claim_result["ok"])
        self.assertTrue(claim_result["execute"])
        self.assertEqual(claim_result["action_type"], "give")
        self.assertEqual(claim_result["item_id"], "minecraft:iron_ingot")
        self.assertEqual(claim_result["item_count"], 4)
        self.assertEqual(claim_result["command"], "/give @s minecraft:iron_ingot 4")
        self.assertIsNone(challenges.get_active_challenge())

        history = challenges.get_challenge_state()["history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["status"], "claimed")
        self.assertEqual(history[0]["reward_item_name"], "железный слиток")

    def test_create_challenge_rejects_second_active_challenge(self):
        first = execute_tool_call(
            "create_challenge",
            {
                "goal_type": "kill",
                "target_query": "зомби",
                "goal_count": 1,
                "reward_item_query": "уголь",
                "reward_count": 1,
            },
        )
        self.assertTrue(first["ok"])

        second = execute_tool_call(
            "create_challenge",
            {
                "goal_type": "collect",
                "target_query": "яблоко",
                "goal_count": 1,
                "reward_item_query": "железо",
                "reward_count": 1,
            },
        )
        self.assertFalse(second["ok"])
        self.assertIn("активный челлендж", second["error"].lower())
