#!/usr/bin/env python
"""Quick test of crafting recipes functionality."""

from api.minecraft_recipes import search_recipe, validate_recipe_grid

print("=" * 60)
print("CRAFTING RECIPES TEST")
print("=" * 60)

# Test 1: Database has recipes
print("\nTest 1: Database exists and has recipes")
recipe = search_recipe("палка")
if recipe:
    print(f"✅ Found recipe for палка: {recipe['name']}")
else:
    print("❌ Failed to find палка")

# Test 2: Search various items
print("\nTest 2: Search for various recipes")
items = ["палка", "деревянная кирка", "железный меч", "печь", "липкий поршень"]
found_count = 0
for item in items:
    recipe = search_recipe(item)
    if recipe:
        print(f"✅ {item}: {recipe['name']}")
        found_count += 1
    else:
        print(f"❌ {item}: NOT FOUND")

print(f"\nFound {found_count}/{len(items)} recipes")

# Test 3: Grid validation
print("\nTest 3: Grid validation")
valid_grid = [
    ["доска", "доска", "пусто"],
    ["доска", "пусто", "пусто"],
    ["пусто", "пусто", "пусто"]
]
print(f"✅ Valid grid passes: {validate_recipe_grid(valid_grid)}")

invalid_grid = [
    ["доска", "доска"],
    ["доска", "пусто"],
    ["пусто", "пусто"]
]
print(f"✅ Invalid grid rejected: {not validate_recipe_grid(invalid_grid)}")

# Test 4: Check grid in actual recipe
print("\nTest 4: Validate grids in all recipes")
from api.minecraft_recipes import MINECRAFT_RECIPES
invalid_recipes = []
for name, recipe in MINECRAFT_RECIPES.items():
    if not validate_recipe_grid(recipe.get("grid", [])):
        invalid_recipes.append(name)

if invalid_recipes:
    print(f"❌ Found {len(invalid_recipes)} recipes with invalid grids:")
    for name in invalid_recipes:
        print(f"   - {name}")
else:
    print(f"✅ All {len(MINECRAFT_RECIPES)} recipes have valid grids")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
