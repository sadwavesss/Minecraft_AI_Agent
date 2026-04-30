import unittest

from api.minecraft_recipes import get_all_recipes, search_recipe, validate_recipe_grid


class CraftingRecipeDatabaseTests(unittest.TestCase):
    def test_database_exists(self):
        self.assertGreater(len(get_all_recipes()), 0, "Recipe database should not be empty")

    def test_recipe_structure(self):
        for name, recipe in get_all_recipes().items():
            self.assertIsInstance(recipe, dict, f"Recipe {name} should be a dict")
            self.assertIn("name", recipe, f"Recipe {name} missing 'name' field")
            self.assertIn("description", recipe, f"Recipe {name} missing 'description' field")
            self.assertIn("grid", recipe, f"Recipe {name} missing 'grid' field")
            self.assertIsInstance(recipe["name"], str, f"Recipe {name} name should be string")
            self.assertIsInstance(recipe["description"], str, f"Recipe {name} description should be string")

    def test_grid_validation(self):
        for name, recipe in get_all_recipes().items():
            grid = recipe.get("grid", [])
            self.assertTrue(validate_recipe_grid(grid), f"Recipe {name} has invalid grid")


class SearchRecipeTests(unittest.TestCase):
    def test_search_exact_match(self):
        recipe = search_recipe("палка")
        self.assertIsNotNone(recipe, "Should find recipe for 'палка'")
        self.assertEqual(recipe["name"], "Палка")

    def test_search_case_insensitive(self):
        recipe1 = search_recipe("палка")
        recipe2 = search_recipe("ПАЛКА")
        recipe3 = search_recipe("ПаЛкА")
        self.assertIsNotNone(recipe1)
        self.assertIsNotNone(recipe2)
        self.assertIsNotNone(recipe3)

    def test_search_partial_match(self):
        recipe = search_recipe("деревянный меч")
        self.assertIsNotNone(recipe, "Should find recipe containing 'деревянный'")

    def test_search_nonexistent(self):
        recipe = search_recipe("волшебная палочка")
        self.assertIsNone(recipe, "Should return None for non-existent recipe")

    def test_search_empty(self):
        recipe = search_recipe("")
        self.assertIsNone(recipe, "Should return None for empty search")

    def test_grid_in_result(self):
        recipe = search_recipe("печь")
        self.assertIsNotNone(recipe)
        self.assertTrue(validate_recipe_grid(recipe.get("grid", [])), "Grid should be valid")


class GridValidationTests(unittest.TestCase):
    def test_valid_grid(self):
        grid = [
            ["доска", "доска", "доска"],
            ["доска", "пусто", "доска"],
            ["доска", "доска", "доска"]
        ]
        self.assertTrue(validate_recipe_grid(grid))

    def test_invalid_not_3x3(self):
        grid = [
            ["доска", "доска", "доска"],
            ["доска", "доска", "доска"]
        ]
        self.assertFalse(validate_recipe_grid(grid))

        grid = [
            ["доска", "доска"],
            ["доска", "доска"],
            ["доска", "доска"]
        ]
        self.assertFalse(validate_recipe_grid(grid))

    def test_invalid_not_list(self):
        self.assertFalse(validate_recipe_grid("not a grid"))
        self.assertFalse(validate_recipe_grid(None))
        self.assertFalse(validate_recipe_grid({}))

    def test_invalid_non_string_items(self):
        grid = [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9]
        ]
        self.assertFalse(validate_recipe_grid(grid))

        grid = [
            ["доска", "доска", None],
            ["доска", "пусто", "доска"],
            ["доска", "доска", "доска"]
        ]
        self.assertFalse(validate_recipe_grid(grid))


class CommonRecipesTests(unittest.TestCase):
    def test_basic_tools(self):
        tools = ["палка", "деревянная кирка", "деревянный топор"]
        for tool in tools:
            recipe = search_recipe(tool)
            self.assertIsNotNone(recipe, f"Recipe for {tool} should exist")

    def test_armor(self):
        armor = ["железный шлем", "железный нагрудник", "железные штаны", "железные сапоги"]
        for item in armor:
            recipe = search_recipe(item)
            self.assertIsNotNone(recipe, f"Recipe for {item} should exist")

    def test_weapons(self):
        weapons = ["деревянный меч", "железный меч", "алмазный меч"]
        for weapon in weapons:
            recipe = search_recipe(weapon)
            self.assertIsNotNone(recipe, f"Recipe for {weapon} should exist")


if __name__ == "__main__":
    unittest.main()
