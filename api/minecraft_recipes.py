"""
Minecraft crafting recipes loader.
Loads recipes from JSON database for proper separation of data and code.
"""

import json
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Path to recipes database
RECIPES_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "minecraft_crafting_recipes.json"
)

# Cache for loaded recipes
_RECIPES_CACHE = None


def _load_recipes() -> dict:
    """Load recipes from JSON file with caching."""
    global _RECIPES_CACHE
    
    if _RECIPES_CACHE is not None:
        return _RECIPES_CACHE
    
    if not os.path.exists(RECIPES_DB_PATH):
        logger.error(f"Recipes database not found at {RECIPES_DB_PATH}")
        return {}
    
    try:
        with open(RECIPES_DB_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _RECIPES_CACHE = data.get("recipes", {})
            logger.info(f"Loaded {len(_RECIPES_CACHE)} recipes from database")
            return _RECIPES_CACHE
    except Exception as e:
        logger.error(f"Failed to load recipes database: {e}")
        return {}


def get_all_recipes() -> dict:
    """Get all available recipes."""
    return _load_recipes()


def search_recipe(query: str) -> Optional[dict]:
    """
    Search for a recipe in the database.
    Returns recipe dict with name, description, and 3x3 grid.
    
    Supports:
    - Exact match: "палка" → finds "палка"
    - Partial match: "железный" → finds "железный меч", "железный шлем", etc.
    - Case-insensitive: "ПАЛКА" → finds "палка"
    """
    recipes = _load_recipes()
    
    if not recipes:
        logger.warning("No recipes loaded from database")
        return None
    
    query_lower = query.lower().strip()
    
    if not query_lower:
        return None
    
    # Try exact match first
    for key in recipes.keys():
        if key.lower() == query_lower:
            return recipes[key]
    
    # Try partial match
    for key, recipe in recipes.items():
        if query_lower in key.lower():
            return recipe
    
    # Try matching in recipe name (not key)
    for recipe in recipes.values():
        name = recipe.get("name", "").lower()
        if query_lower in name:
            return recipe
    
    return None


def validate_recipe_grid(grid: list) -> bool:
    """
    Validate that recipe grid is proper 3x3 array.
    
    Requirements:
    - Must be a list
    - Must have exactly 3 rows
    - Each row must be a list with exactly 3 items
    - All items must be strings
    """
    if not isinstance(grid, list) or len(grid) != 3:
        return False
    
    for row in grid:
        if not isinstance(row, list) or len(row) != 3:
            return False
        for item in row:
            if not isinstance(item, str):
                return False
    
    return True


def validate_all_recipes() -> dict:
    """
    Validate all recipes in the database.
    
    Returns:
        dict with 'valid' (list of valid recipe keys) and 'invalid' (list of problems)
    """
    recipes = _load_recipes()
    result = {
        "valid": [],
        "invalid": []
    }
    
    for name, recipe in recipes.items():
        errors = []
        
        # Check structure
        if not isinstance(recipe, dict):
            errors.append(f"Not a dict")
        else:
            if "name" not in recipe or not isinstance(recipe.get("name"), str):
                errors.append(f"Missing or invalid 'name'")
            if "description" not in recipe or not isinstance(recipe.get("description"), str):
                errors.append(f"Missing or invalid 'description'")
            if "grid" not in recipe:
                errors.append(f"Missing 'grid'")
            elif not validate_recipe_grid(recipe.get("grid")):
                errors.append(f"Invalid grid format (must be 3x3 strings)")
        
        if errors:
            result["invalid"].append({
                "name": name,
                "errors": errors
            })
        else:
            result["valid"].append(name)
    
    return result

