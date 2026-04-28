import unittest
from types import SimpleNamespace

from api.player_state import (
    apply_log_to_player_state,
    get_player_state,
    get_player_state_prompt_context,
    reset_player_state,
)


class PlayerStateTests(unittest.TestCase):
    def setUp(self):
        reset_player_state()

    def test_apply_mob_kill_updates_counts_and_recent_history(self):
        entry = SimpleNamespace(
            event_type="mob_kill",
            event_data={"entity_id": "minecraft:zombie", "entity_name": "Зомби", "count_delta": 2},
            timestamp=None,
        )

        apply_log_to_player_state(entry)
        state = get_player_state()

        self.assertEqual(state["kill_counts"]["minecraft:zombie"], 2)
        self.assertEqual(state["kill_total"], 2)
        self.assertEqual(state["recent_kills"][-1]["entity_name"], "Зомби")

    def test_apply_inventory_snapshot_replaces_inventory_summary(self):
        entry = SimpleNamespace(
            event_type="inventory_snapshot",
            event_data={
                "counts": {"minecraft:coal": 12, "minecraft:diamond_sword": 1},
                "hotbar": [{"slot": "hotbar_0", "item_id": "minecraft:diamond_sword", "display_name": "Алмазный меч", "count": 1}],
                "armor": [{"slot": "helmet", "item_id": "minecraft:iron_helmet", "display_name": "Железный шлем", "count": 1}],
                "offhand": [{"slot": "offhand", "item_id": "minecraft:torch", "display_name": "Факел", "count": 32}],
            },
            timestamp=None,
        )

        apply_log_to_player_state(entry)
        state = get_player_state()

        self.assertEqual(state["inventory"]["counts"]["minecraft:coal"], 12)
        self.assertEqual(state["inventory"]["hotbar"][0]["item_id"], "minecraft:diamond_sword")
        self.assertEqual(state["inventory"]["armor"][0]["slot"], "helmet")
        self.assertEqual(state["inventory"]["offhand"][0]["count"], 32)
        self.assertEqual(state["inventory"]["count_entries"][0]["display_name"], "уголь")

    def test_player_state_exposes_localized_web_entries(self):
        apply_log_to_player_state(
            SimpleNamespace(
                event_type="mob_kill",
                event_data={"entity_id": "minecraft:zombie", "entity_name": "", "count_delta": 2},
                timestamp=None,
            )
        )
        apply_log_to_player_state(
            SimpleNamespace(
                event_type="inventory_snapshot",
                event_data={"counts": {"minecraft:coal": 5}, "hotbar": [], "armor": [], "offhand": []},
                timestamp=None,
            )
        )
        state = get_player_state()

        self.assertEqual(state["kill_count_entries"][0]["display_name"], "зомби")
        self.assertEqual(state["inventory"]["count_entries"][0]["display_name"], "уголь")

    def test_prompt_context_includes_kills_and_inventory(self):
        apply_log_to_player_state(
            SimpleNamespace(
                event_type="mob_kill",
                event_data={"entity_id": "minecraft:creeper", "entity_name": "Крипер", "count_delta": 1},
                timestamp=None,
            )
        )
        apply_log_to_player_state(
            SimpleNamespace(
                event_type="inventory_snapshot",
                event_data={
                    "counts": {"minecraft:coal": 8},
                    "hotbar": [{"slot": "hotbar_1", "item_id": "minecraft:coal", "display_name": "Уголь", "count": 8}],
                    "armor": [],
                    "offhand": [],
                },
                timestamp=None,
            )
        )

        context = get_player_state_prompt_context()
        self.assertIn("крипер", context)
        self.assertIn("уголь x8", context)
