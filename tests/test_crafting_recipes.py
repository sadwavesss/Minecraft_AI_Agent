"""
Tests for Minecraft crafting recipes functionality.
"""

import pytest
from api.minecraft_recipes import search_recipe, validate_recipe_grid, MINECRAFT_RECIPES


class TestCraftingRecipeDatabase:
    """Test the crafting recipe database."""
    
    def test_database_exists(self):
        """Test that recipe database is not empty."""
        assert len(MINECRAFT_RECIPES) > 0, "Recipe database should not be empty"
    
    def test_recipe_structure(self):
        """Test that all recipes have correct structure."""
        for name, recipe in MINECRAFT_RECIPES.items():
            assert isinstance(recipe, dict), f"Recipe {name} should be a dict"
            assert "name" in recipe, f"Recipe {name} missing 'name' field"
            assert "description" in recipe, f"Recipe {name} missing 'description' field"
            assert "grid" in recipe, f"Recipe {name} missing 'grid' field"
            assert isinstance(recipe["name"], str), f"Recipe {name} name should be string"
            assert isinstance(recipe["description"], str), f"Recipe {name} description should be string"
    
    def test_grid_validation(self):
        """Test that all recipe grids are valid 3x3 arrays."""
        for name, recipe in MINECRAFT_RECIPES.items():
            grid = recipe.get("grid", [])
            assert validate_recipe_grid(grid), f"Recipe {name} has invalid grid"


class TestSearchRecipe:
    """Test recipe search functionality."""
    
    def test_search_exact_match(self):
        """Test searching for exact recipe names."""
        recipe = search_recipe("палка")
        assert recipe is not None, "Should find recipe for 'палка'"
        assert recipe["name"] == "Палка"
    
    def test_search_case_insensitive(self):
        """Test that search is case-insensitive."""
        recipe1 = search_recipe("палка")
        recipe2 = search_recipe("ПАЛКА")
        recipe3 = search_recipe("ПаЛкА")
        assert recipe1 is not None
        assert recipe2 is not None
        assert recipe3 is not None
    
    def test_search_partial_match(self):
        """Test that search works with partial names."""
        recipe = search_recipe("деревянный меч")
        assert recipe is not None, "Should find recipe containing 'деревянный'"
    
    def test_search_nonexistent(self):
        """Test searching for non-existent recipe."""
        recipe = search_recipe("волшебная палочка")
        assert recipe is None, "Should return None for non-existent recipe"
    
    def test_search_empty(self):
        """Test searching with empty string."""
        recipe = search_recipe("")
        assert recipe is None, "Should return None for empty search"
    
    def test_grid_in_result(self):
        """Test that returned recipe has valid grid."""
        recipe = search_recipe("печь")
        assert recipe is not None
        assert validate_recipe_grid(recipe.get("grid", [])), "Grid should be valid"


class TestGridValidation:
    """Test grid validation function."""
    
    def test_valid_grid(self):
        """Test validation of correct 3x3 grid."""
        grid = [
            ["доска", "доска", "доска"],
            ["доска", "пусто", "доска"],
            ["доска", "доска", "доска"]
        ]
        assert validate_recipe_grid(grid) is True
    
    def test_invalid_not_3x3(self):
        """Test that non-3x3 grids are rejected."""
        # 2x3 grid
        grid = [
            ["доска", "доска", "доска"],
            ["доска", "доска", "доска"]
        ]
        assert validate_recipe_grid(grid) is False
        
        # 3x2 grid
        grid = [
            ["доска", "доска"],
            ["доска", "доска"],
            ["доска", "доска"]
        ]
        assert validate_recipe_grid(grid) is False
    
    def test_invalid_not_list(self):
        """Test that non-list is rejected."""
        assert validate_recipe_grid("not a grid") is False
        assert validate_recipe_grid(None) is False
        assert validate_recipe_grid({}) is False
    
    def test_invalid_non_string_items(self):
        """Test that grids with non-string items are rejected."""
        grid = [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9]
        ]
        assert validate_recipe_grid(grid) is False
        
        grid = [
            ["доска", "доска", None],
            ["доска", "пусто", "доска"],
            ["доска", "доска", "доска"]
        ]
        assert validate_recipe_grid(grid) is False


class TestCommonRecipes:
    """Test that common recipes are available."""
    
    def test_basic_tools(self):
        """Test that basic tools are in database."""
        tools = ["палка", "деревянная кирка", "деревянный топор"]
        for tool in tools:
            recipe = search_recipe(tool)
            assert recipe is not None, f"Recipe for {tool} should exist"
    
    def test_armor(self):
        """Test that armor recipes are available."""
        armor = ["железный шлем", "железный нагрудник", "железные штаны", "железные сапоги"]
        for item in armor:
            recipe = search_recipe(item)
            assert recipe is not None, f"Recipe for {item} should exist"
    
    def test_weapons(self):
        """Test that weapon recipes are available."""
        weapons = ["деревянный меч", "железный меч", "алмазный меч"]
        for weapon in weapons:
            recipe = search_recipe(weapon)
            assert recipe is not None, f"Recipe for {weapon} should exist"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
