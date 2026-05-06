import unittest
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from api import advice
from api.challenges import reset_challenge_state
from api.player_state import reset_player_state
from api.tool_service import execute_tool_call, get_tool_registry
from models.groq_response import ChatMessage


class ActionParsingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        advice.logs_db.clear()
        advice._response_history.clear()
        advice._conversation_history.clear()
        advice._last_rp_response = None
        advice._last_rp_response_time = 0
        reset_player_state()
        reset_challenge_state()

    def test_extract_requested_item_id_supports_russian_aliases(self):
        self.assertEqual(advice._extract_requested_item_id("дай мне меч"), "minecraft:diamond_sword")
        self.assertEqual(advice._extract_requested_item_id("выдай 3 яблока"), "minecraft:apple")
        self.assertEqual(advice._extract_requested_item_id("дай мне алмазную кирку"), "minecraft:diamond_pickaxe")
        self.assertEqual(advice._extract_requested_item_id("дай блок земли"), "minecraft:dirt")

    def test_extract_requested_count_defaults_and_limits(self):
        self.assertEqual(advice._extract_requested_count("дай яблоко"), 1)
        self.assertEqual(advice._extract_requested_count("дай 3 яблока"), 3)
        self.assertEqual(advice._extract_requested_count("дай 128 яблок"), 64)

    def test_build_direct_action_payload_for_russian_request(self):
        payload = advice._build_direct_action_payload("дай 3 яблока")
        self.assertIsNotNone(payload)
        self.assertEqual(payload["mode"], "action")
        self.assertEqual(payload["action_type"], "give")
        self.assertEqual(payload["item_id"], "minecraft:apple")
        self.assertEqual(payload["count"], 3)
        self.assertTrue(payload["execute"])

    def test_build_direct_action_payload_for_block_request(self):
        payload = advice._build_direct_action_payload("дай мне блок земли")
        self.assertIsNotNone(payload)
        self.assertEqual(payload["item_id"], "minecraft:dirt")

    def test_build_chat_action_response_rejects_unsupported_action(self):
        last = SimpleNamespace(player_health=20.0, threats_detected=[])
        result = advice._build_chat_action_response(
            {
                "mode": "action",
                "spoken_response": "Пробую телепортировать.",
                "tool_name": "teleport",
                "arguments": {"target": "@s"},
            },
            last,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.mode, "action")
        self.assertFalse(result.execute)
        self.assertIn("give_item", result.error)

    def test_build_chat_action_response_supports_tool_schema(self):
        last = SimpleNamespace(player_health=20.0, threats_detected=[])
        result = advice._build_chat_action_response(
            {
                "mode": "action",
                "spoken_response": "Сейчас выдам.",
                "tool_name": "give_item",
                "arguments": {"item_query": "наковален", "count": 10},
                "should_execute": True,
            },
            last,
        )
        self.assertIsNotNone(result)
        self.assertTrue(result.execute)
        self.assertEqual(result.item_id, "minecraft:anvil")
        self.assertEqual(result.item_count, 10)
        self.assertEqual(result.command, "/give @s minecraft:anvil 10")

    def test_build_chat_action_response_allows_persona_refusal(self):
        last = SimpleNamespace(player_health=20.0, threats_detected=[])
        result = advice._build_chat_action_response(
            {
                "mode": "action",
                "spoken_response": "Не-а, пузырёк сперва заслужи.",
                "tool_name": "give_item",
                "arguments": {"item_query": "пузырька", "count": 1},
                "should_execute": False,
            },
            last,
        )
        self.assertIsNotNone(result)
        self.assertFalse(result.execute)
        self.assertEqual(result.item_id, "minecraft:glass_bottle")
        self.assertIsNone(result.command)
        self.assertIn("заслужи", result.response.lower())

    async def test_player_chat_message_handles_russian_request_without_llm(self):
        with patch.object(advice.groq_client, "is_available", return_value=False):
            result = await advice.player_chat_message(ChatMessage(text="дай мне меч"))

        self.assertEqual(result.mode, "action")
        self.assertTrue(result.execute)
        self.assertEqual(result.item_id, "minecraft:diamond_sword")
        self.assertEqual(result.command, "/give @s minecraft:diamond_sword 1")

    async def test_player_chat_message_returns_ambiguity_error_for_catalog_conflict(self):
        with patch.object(advice.groq_client, "is_available", return_value=False):
            result = await advice.player_chat_message(ChatMessage(text="дай доски"))

        self.assertEqual(result.mode, "action")
        self.assertFalse(result.execute)
        self.assertIn("неоднознач", result.error.lower())

    async def test_player_chat_message_returns_action_error_for_unknown_item_without_llm(self):
        with patch.object(advice.groq_client, "is_available", return_value=False):
            result = await advice.player_chat_message(ChatMessage(text="дай мне гипербластер"))

        self.assertEqual(result.mode, "action")
        self.assertFalse(result.execute)
        self.assertIn("не могу выполнить выдачу", result.error.lower())

    async def test_get_compact_status_returns_active_challenge_snapshot(self):
        execute_tool_call(
            "create_challenge",
            {
                "goal_type": "kill",
                "target_query": "зомби",
                "goal_count": 1,
                "reward_item_query": "уголь",
                "reward_count": 2,
            },
        )
        advice._last_rp_response = {"response": "Держись ближе к укрытию.", "level": "WARNING"}

        payload = await advice.get_compact_status()

        self.assertEqual(payload["advice"], "Держись ближе к укрытию.")
        self.assertEqual(payload["advice_level"], "WARNING")
        self.assertIsNotNone(payload["challenge"])
        self.assertEqual(payload["challenge"]["title"], "Охота")
        self.assertEqual(payload["challenge"]["progress"], "0/1")
        self.assertEqual(payload["challenge"]["reward"], "уголь")

    async def test_player_chat_message_handles_summon_request_without_llm(self):
        with patch.object(advice.groq_client, "is_available", return_value=False):
            result = await advice.player_chat_message(ChatMessage(text="призови зомби"))

        self.assertEqual(result.mode, "action")
        self.assertTrue(result.execute)
        self.assertEqual(result.action_type, "summon")
        self.assertEqual(result.entity_id, "minecraft:zombie")
        self.assertEqual(result.command, "/summon minecraft:zombie ~ ~ ~")

    async def test_player_chat_message_handles_multi_summon_request_without_llm(self):
        with patch.object(advice.groq_client, "is_available", return_value=False):
            result = await advice.player_chat_message(ChatMessage(text="призови 3 зомби"))

        self.assertEqual(result.mode, "action")
        self.assertTrue(result.execute)
        self.assertEqual(result.action_type, "summon")
        self.assertEqual(result.entity_id, "minecraft:zombie")
        self.assertEqual(result.entity_count, 3)
        self.assertEqual(
            result.command,
            "/summon minecraft:zombie ~ ~ ~\n/summon minecraft:zombie ~ ~ ~\n/summon minecraft:zombie ~ ~ ~",
        )

    async def test_player_chat_message_handles_remove_request_without_llm(self):
        with patch.object(advice.groq_client, "is_available", return_value=False):
            result = await advice.player_chat_message(ChatMessage(text="забери 3 угля"))

        self.assertEqual(result.mode, "action")
        self.assertTrue(result.execute)
        self.assertEqual(result.action_type, "clear")
        self.assertEqual(result.item_id, "minecraft:coal")
        self.assertEqual(result.item_count, 3)
        self.assertEqual(result.command, "/clear @s minecraft:coal 3")

    async def test_player_chat_message_uses_llm_tool_for_indirect_plural_request(self):
        decision = {
            "assistant_response": None,
            "tool_call": {"name": "give_item", "arguments": {"item_query": "наковален", "count": 10}},
        }
        with (
            patch.object(advice.groq_client, "is_available", return_value=True),
            patch.object(advice.groq_client, "generate_tool_decision_async", new=AsyncMock(return_value=decision)),
            patch.object(advice.groq_client, "generate_tool_followup_async", new=AsyncMock(return_value="Ладно, держи наковальни.")),
        ):
            result = await advice.player_chat_message(ChatMessage(text="мне бы 10 наковален"))

        self.assertEqual(result.mode, "action")
        self.assertTrue(result.execute)
        self.assertEqual(result.item_id, "minecraft:anvil")
        self.assertEqual(result.command, "/give @s minecraft:anvil 10")

    async def test_player_chat_message_uses_llm_tool_for_soft_phrase(self):
        decision = {
            "assistant_response": None,
            "tool_call": {"name": "give_item", "arguments": {"item_query": "пузырька", "count": 1}},
        }
        with (
            patch.object(advice.groq_client, "is_available", return_value=True),
            patch.object(advice.groq_client, "generate_tool_decision_async", new=AsyncMock(return_value=decision)),
            patch.object(advice.groq_client, "generate_tool_followup_async", new=AsyncMock(return_value="Ну держи пузырёк, раз так просишь.")),
        ):
            result = await advice.player_chat_message(ChatMessage(text="Я бы не отказался сейчас от пузырька"))

        self.assertEqual(result.mode, "action")
        self.assertTrue(result.execute)
        self.assertEqual(result.item_id, "minecraft:glass_bottle")

    async def test_player_chat_message_uses_llm_tool_for_summon_request(self):
        decision = {
            "assistant_response": None,
            "tool_call": {"name": "summon_entity", "arguments": {"entity_query": "скелета", "count": 1}},
        }
        with (
            patch.object(advice.groq_client, "is_available", return_value=True),
            patch.object(advice.groq_client, "generate_tool_decision_async", new=AsyncMock(return_value=decision)),
            patch.object(advice.groq_client, "generate_tool_followup_async", new=AsyncMock(return_value="Ладно, зову скелета.")),
        ):
            result = await advice.player_chat_message(ChatMessage(text="заспавни мне скелета"))

        self.assertEqual(result.mode, "action")
        self.assertTrue(result.execute)
        self.assertEqual(result.action_type, "summon")
        self.assertEqual(result.entity_id, "minecraft:skeleton")
        self.assertEqual(result.command, "/summon minecraft:skeleton ~ ~ ~")

    async def test_get_rp_response_returns_pending_challenge_reward_action(self):
        execute_tool_call(
            "create_challenge",
            {
                "goal_type": "kill",
                "target_query": "зомби",
                "goal_count": 1,
                "reward_item_query": "уголь",
                "reward_count": 2,
            },
        )
        from api.player_state import apply_log_to_player_state
        from models.log_entry import LogEntry

        apply_log_to_player_state(
            LogEntry(
                level="INFO",
                event_type="mob_kill",
                event_data={"entity_id": "minecraft:zombie", "entity_name": "Zombie", "count_delta": 1},
            )
        )
        advice.refresh_challenge_progress()

        result = await advice.get_rp_response()

        self.assertEqual(result.mode, "action")
        self.assertTrue(result.execute)
        self.assertEqual(result.action_type, "give")
        self.assertEqual(result.item_id, "minecraft:coal")
        self.assertEqual(result.item_count, 2)

    async def test_player_chat_message_explains_that_challenge_rewards_are_automatic(self):
        with patch.object(advice.groq_client, "is_available", return_value=False):
            result = await advice.player_chat_message(ChatMessage(text="забрать награду за челлендж"))

        self.assertEqual(result.mode, "chat")
        self.assertFalse(result.execute)
        self.assertIn("автоматически", result.response.lower())

    async def test_player_chat_message_returns_refusal_without_execution(self):
        decision = {
            "assistant_response": "Нет уж, сегодня без подарков.",
            "tool_call": None,
        }
        with (
            patch.object(advice.groq_client, "is_available", return_value=True),
            patch.object(advice.groq_client, "generate_tool_decision_async", new=AsyncMock(return_value=decision)),
        ):
            result = await advice.player_chat_message(ChatMessage(text="мне бы меч"))

        self.assertEqual(result.mode, "chat")
        self.assertFalse(result.execute)
        self.assertIsNone(result.item_id)
        self.assertIsNone(result.command)

    async def test_get_rp_response_returns_cached_response_when_llm_tip_times_out(self):
        advice.logs_db.append(
            SimpleNamespace(
                event_type="death",
                event_data={"cause": "fall"},
                player_health=0.0,
                threats_detected=[],
            )
        )
        advice._last_rp_response = {
            "response": "[RP] Старый, но быстрый ответ.",
            "confidence": 0.8,
            "level": "INFO",
            "threats": [],
            "source": "ollama",
        }

        async def slow_tip(_recent_logs):
            await asyncio.sleep(0.05)
            return "Новый медленный ответ"

        with (
            patch.object(advice.groq_client, "is_available", return_value=True),
            patch.object(advice.groq_client, "generate_tip_async", new=slow_tip),
            patch.object(advice.groq_client, "get_source_name", return_value="ollama"),
            patch.object(advice, "RP_LLM_TIMEOUT_SECONDS", 0.001),
        ):
            result = await advice.get_rp_response()

        self.assertEqual(result.response, "[RP] Старый, но быстрый ответ.")
        self.assertEqual(result.source, "ollama")

    async def test_get_rp_response_skips_llm_for_routine_polling(self):
        advice.logs_db.append(
            SimpleNamespace(
                event_type="state",
                event_data={"health": 20.0, "food": 20},
                player_health=20.0,
                threats_detected=[],
            )
        )
        tip_mock = AsyncMock(return_value="Ненужный ответ модели")

        with (
            patch.object(advice.groq_client, "is_available", return_value=True),
            patch.object(advice.groq_client, "generate_tip_async", new=tip_mock),
        ):
            result = await advice.get_rp_response()

        self.assertEqual(result.source, "fallback")
        self.assertEqual(result.response, "")
        self.assertEqual(tip_mock.await_count, 0)

    async def test_get_rp_response_falls_back_when_llm_tip_times_out_without_cache(self):
        advice.logs_db.append(
            SimpleNamespace(
                event_type="low_health",
                event_data={"health": 4.0, "food": 6},
                player_health=4.0,
                threats_detected=[],
            )
        )

        async def slow_tip(_recent_logs):
            await asyncio.sleep(0.05)
            return "Слишком поздний ответ"

        with (
            patch.object(advice.groq_client, "is_available", return_value=True),
            patch.object(advice.groq_client, "generate_tip_async", new=slow_tip),
            patch.object(advice.groq_client, "get_source_name", return_value="ollama"),
            patch.object(advice, "RP_LLM_TIMEOUT_SECONDS", 0.001),
        ):
            result = await advice.get_rp_response()

        self.assertEqual(result.source, "fallback")
        self.assertEqual(result.response, "")

    async def test_player_chat_message_uses_single_structured_llm_call(self):
        payload = {"assistant_response": "Привет, друже.", "tool_call": None}
        structured_mock = AsyncMock(return_value=payload)
        followup_mock = AsyncMock(return_value="Этот вызов не должен происходить")

        with (
            patch.object(advice.groq_client, "is_available", return_value=True),
            patch.object(advice.groq_client, "generate_tool_decision_async", new=structured_mock),
            patch.object(advice.groq_client, "generate_tool_followup_async", new=followup_mock),
        ):
            result = await advice.player_chat_message(ChatMessage(text="привет"))

        self.assertEqual(result.mode, "chat")
        self.assertIn("Привет", result.response)
        self.assertEqual(structured_mock.await_count, 1)
        self.assertEqual(followup_mock.await_count, 0)

    async def test_player_chat_message_falls_back_to_regular_llm_chat_when_tool_decision_is_invalid(self):
        with (
            patch.object(advice.groq_client, "is_available", return_value=True),
            patch.object(advice.groq_client, "generate_tool_decision_async", new=AsyncMock(return_value=None)),
            patch.object(advice.groq_client, "generate_chat_response_async", new=AsyncMock(return_value="Не туплю, просто отвечаю нормально.")),
        ):
            result = await advice.player_chat_message(ChatMessage(text="ну и что скажешь?"))

        self.assertEqual(result.mode, "chat")
        self.assertIn("отвечаю нормально", result.response)

    async def test_player_chat_message_passes_recent_conversation_history(self):
        first_payload = {"assistant_response": "Я помню наш разговор.", "tool_call": None}
        second_payload = {"assistant_response": "Да, ты только что здоровался.", "tool_call": None}
        structured_mock = AsyncMock(side_effect=[first_payload, second_payload])

        with patch.object(advice.groq_client, "is_available", return_value=True), patch.object(
            advice.groq_client, "generate_tool_decision_async", new=structured_mock
        ):
            await advice.player_chat_message(ChatMessage(text="привет"))
            await advice.player_chat_message(ChatMessage(text="помнишь, что я сказал?"))

        second_call_args = structured_mock.await_args_list[1].args
        self.assertEqual(second_call_args[0], "помнишь, что я сказал?")
        conversation_history = second_call_args[2]
        self.assertTrue(conversation_history)
        self.assertEqual(conversation_history[0]["role"], "user")
        self.assertIn("привет", conversation_history[0]["content"].lower())
        self.assertEqual(conversation_history[1]["role"], "assistant")

    def test_conversation_history_is_trimmed_to_window(self):
        for idx in range(14):
            advice._append_conversation_message("user", f"msg {idx}")

        window = advice._conversation_window()
        self.assertEqual(len(window), advice.MAX_CONVERSATION_HISTORY)
        self.assertEqual(window[0]["content"], "msg 4")
        self.assertEqual(window[-1]["content"], "msg 13")

    async def test_player_chat_message_supports_followup_tool_continuation(self):
        first_decision = {
            "assistant_response": None,
            "tool_call": {"name": "give_item", "arguments": {"item_query": "меч", "count": 1}},
        }
        second_decision = {
            "assistant_response": None,
            "tool_call": {"name": "give_item", "arguments": {"item_query": "уголь", "count": 1}},
        }
        decision_mock = AsyncMock(side_effect=[first_decision, second_decision])
        followup_mock = AsyncMock(side_effect=["Держи меч.", "И ещё немного угля."])

        with (
            patch.object(advice.groq_client, "is_available", return_value=True),
            patch.object(advice.groq_client, "generate_tool_decision_async", new=decision_mock),
            patch.object(advice.groq_client, "generate_tool_followup_async", new=followup_mock),
        ):
            first = await advice.player_chat_message(ChatMessage(text="дай мне меч"))
            second = await advice.player_chat_message(ChatMessage(text="и ещё уголь"))

        self.assertTrue(first.execute)
        self.assertEqual(first.item_id, "minecraft:diamond_sword")
        self.assertTrue(second.execute)
        self.assertEqual(second.item_id, "minecraft:coal")
        second_history = decision_mock.await_args_list[1].args[2]
        serialized_history = " ".join(entry["content"] for entry in second_history if "content" in entry)
        self.assertIn("give_item", serialized_history)
        self.assertIn("diamond_sword", serialized_history)

    async def test_player_chat_message_supports_followup_summon_continuation(self):
        first_decision = {
            "assistant_response": None,
            "tool_call": {"name": "summon_entity", "arguments": {"entity_query": "зомби", "count": 1}},
        }
        second_decision = {
            "assistant_response": None,
            "tool_call": {"name": "summon_entity", "arguments": {"entity_query": "крипера", "count": 1}},
        }
        decision_mock = AsyncMock(side_effect=[first_decision, second_decision])
        followup_mock = AsyncMock(side_effect=["Зову зомби.", "И ещё крипера."])

        with (
            patch.object(advice.groq_client, "is_available", return_value=True),
            patch.object(advice.groq_client, "generate_tool_decision_async", new=decision_mock),
            patch.object(advice.groq_client, "generate_tool_followup_async", new=followup_mock),
        ):
            first = await advice.player_chat_message(ChatMessage(text="призови зомби"))
            second = await advice.player_chat_message(ChatMessage(text="и ещё крипера"))

        self.assertTrue(first.execute)
        self.assertEqual(first.entity_id, "minecraft:zombie")
        self.assertTrue(second.execute)
        self.assertEqual(second.entity_id, "minecraft:creeper")
        second_history = decision_mock.await_args_list[1].args[2]
        serialized_history = " ".join(entry["content"] for entry in second_history if "content" in entry)
        self.assertIn("summon_entity", serialized_history)
        self.assertIn("minecraft:zombie", serialized_history)

    def test_tool_registry_exposes_give_item(self):
        tools = get_tool_registry()
        self.assertEqual(tools[0]["name"], "give_item")
        self.assertEqual(tools[1]["name"], "remove_item")
        self.assertEqual(tools[2]["name"], "summon_entity")
        self.assertEqual(tools[3]["name"], "create_challenge")
        self.assertEqual(len(tools), 4)

    def test_execute_tool_call_resolves_give_item(self):
        result = execute_tool_call("give_item", {"item_query": "уголь", "count": 5})
        self.assertTrue(result["ok"])
        self.assertEqual(result["item_id"], "minecraft:coal")
        self.assertEqual(result["item_count"], 5)

    def test_execute_tool_call_resolves_remove_item(self):
        result = execute_tool_call("remove_item", {"item_query": "уголь", "count": 2})
        self.assertTrue(result["ok"])
        self.assertEqual(result["action_type"], "clear")
        self.assertEqual(result["item_id"], "minecraft:coal")
        self.assertEqual(result["command"], "/clear @s minecraft:coal 2")

    def test_execute_tool_call_resolves_summon_entity(self):
        result = execute_tool_call("summon_entity", {"entity_query": "крипера", "count": 1})
        self.assertTrue(result["ok"])
        self.assertEqual(result["entity_id"], "minecraft:creeper")
        self.assertEqual(result["command"], "/summon minecraft:creeper ~ ~ ~")

    def test_execute_tool_call_supports_multi_summon_entity(self):
        result = execute_tool_call("summon_entity", {"entity_query": "зомби", "count": 3})
        self.assertTrue(result["ok"])
        self.assertEqual(result["entity_id"], "minecraft:zombie")
        self.assertEqual(result["entity_count"], 3)
        self.assertEqual(
            result["command"],
            "/summon minecraft:zombie ~ ~ ~\n/summon minecraft:zombie ~ ~ ~\n/summon minecraft:zombie ~ ~ ~",
        )
