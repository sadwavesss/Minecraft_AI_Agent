import unittest

from api.entity_catalog import resolve_entity_id_from_text, search_entity_catalog


class EntityCatalogTests(unittest.TestCase):
    def test_resolve_basic_russian_entity_request(self):
        result = resolve_entity_id_from_text("призови зомби")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["entity_id"], "minecraft:zombie")

    def test_resolve_entity_alias_in_russian_case(self):
        result = resolve_entity_id_from_text("заспавни мне скелета")
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["entity_id"], "minecraft:skeleton")

    def test_search_entity_catalog_returns_ranked_match(self):
        matches = search_entity_catalog("крипера пожалуйста")
        self.assertTrue(matches)
        self.assertEqual(matches[0]["id"], "minecraft:creeper")

    def test_resolve_unknown_entity(self):
        result = resolve_entity_id_from_text("призови гипердракона")
        self.assertEqual(result["status"], "not_found")
