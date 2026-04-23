import unittest

from api.minecraft_catalog import resolve_item_id_from_text, search_catalog


class MinecraftCatalogTests(unittest.TestCase):
    def test_resolve_block_requests_in_russian(self):
        result = resolve_item_id_from_text("дай блок земли")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["item_id"], "minecraft:dirt")

        result = resolve_item_id_from_text("выдай мне камень")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["item_id"], "minecraft:stone")

    def test_resolve_specific_planks(self):
        result = resolve_item_id_from_text("дай дубовые доски")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["item_id"], "minecraft:oak_planks")

    def test_report_ambiguous_catalog_query(self):
        result = resolve_item_id_from_text("дай доски")
        self.assertEqual(result["status"], "ambiguous")
        self.assertGreaterEqual(len(result["matches"]), 2)

    def test_search_catalog_returns_ranked_matches(self):
        matches = search_catalog("шалкеровый ящик")
        self.assertTrue(matches)
        self.assertEqual(matches[0]["id"], "minecraft:shulker_box")

    def test_resolve_synonym_like_butylyok_for_glass_bottle(self):
        result = resolve_item_id_from_text("я бы сейчас не отказался от бутылька")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["item_id"], "minecraft:glass_bottle")

    def test_search_catalog_handles_soft_request_noise(self):
        matches = search_catalog("мне бы 10 наковален пожалуйста")
        self.assertTrue(matches)
        self.assertEqual(matches[0]["id"], "minecraft:anvil")
