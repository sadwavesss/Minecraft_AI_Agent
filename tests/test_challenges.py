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

        self.assertIsNone(challenges.get_active_challenge())
        state = challenges.get_challenge_state()
        history = state["history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["progress_count"], 1)
        self.assertEqual(history[0]["status"], "rewarded")
        self.assertEqual(history[0]["goal_target_name"], "зомби")
        self.assertEqual(len(state["pending_rewards"]), 1)

    def test_completed_collect_challenge_queues_reward_action_and_clears_active(self):
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

        self.assertIsNone(challenges.get_active_challenge())

        history = challenges.get_challenge_state()["history"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["status"], "rewarded")
        self.assertEqual(history[0]["reward_item_name"], "железный слиток")
        self.assertEqual(history[0]["reward_status"], "issued")

        pending_reward = challenges.consume_pending_reward_action()
        self.assertIsNotNone(pending_reward)
        self.assertTrue(pending_reward["execute"])
        self.assertEqual(pending_reward["action_type"], "give")
        self.assertEqual(pending_reward["item_id"], "minecraft:iron_ingot")
        self.assertEqual(pending_reward["item_count"], 4)
        self.assertEqual(pending_reward["command"], "/give @s minecraft:iron_ingot 4")

    def test_claim_completed_challenge_returns_already_issued_for_rewarded_history(self):
        result = execute_tool_call(
            "create_challenge",
            {
                "goal_type": "kill",
                "target_query": "зомби",
                "goal_count": 1,
                "reward_item_query": "уголь",
                "reward_count": 2,
            },
        )
        self.assertTrue(result["ok"])
        challenge_id = result["challenge"]["id"]

        apply_log_to_player_state(
            LogEntry(
                level="INFO",
                event_type="mob_kill",
                event_data={"entity_id": "minecraft:zombie", "entity_name": "Zombie", "count_delta": 1},
            )
        )
        challenges.refresh_challenge_progress()

        claim_result = execute_tool_call("claim_challenge_reward", {"challenge_id": challenge_id})
        self.assertTrue(claim_result["ok"])
        self.assertFalse(claim_result["execute"])
        self.assertIn("автоматически", claim_result["summary"])

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

    def test_create_challenge_description_uses_localized_names(self):
        result = execute_tool_call(
            "create_challenge",
            {
                "goal_type": "kill",
                "target_query": "зомби",
                "goal_count": 2,
                "reward_item_query": "железо",
                "reward_count": 3,
            },
        )
        self.assertTrue(result["ok"])
        challenge = result["challenge"]
        self.assertIn("зомби", challenge["description"].lower())
        self.assertIn("железный слиток", challenge["description"].lower())
        self.assertNotIn("minecraft:", challenge["description"])
