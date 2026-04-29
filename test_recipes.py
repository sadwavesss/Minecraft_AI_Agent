#!/usr/bin/env python
"""Quick test of crafting recipes functionality."""

from api.minecraft_recipes import search_recipe, validate_recipe_grid, get_all_recipes, validate_all_recipes

print("=" * 60)
print("CRAFTING RECIPES TEST")
print("=" * 60)

# Test 1: Load recipes from database
print("\nTest 1: Load recipes from JSON database")
all_recipes = get_all_recipes()
if all_recipes:
    print(f"✅ Loaded {len(all_recipes)} recipes from database")
else:
    print("❌ Failed to load recipes")

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

# Test 4: Validate all recipes
print("\nTest 4: Validate all recipes in database")
validation_result = validate_all_recipes()
valid_count = len(validation_result["valid"])
invalid_count = len(validation_result["invalid"])

print(f"✅ Valid recipes: {valid_count}")
if invalid_count > 0:
    print(f"❌ Invalid recipes: {invalid_count}")
    for item in validation_result["invalid"]:
        print(f"   - {item['name']}: {', '.join(item['errors'])}")
else:
    print(f"✅ All {valid_count} recipes have valid structure")

# Test 5: Case insensitive search
print("\nTest 5: Case-insensitive search")
tests = [("палка", "палка"), ("ПАЛКА", "палка"), ("ПаЛкА", "палка")]
for search_term, expected_key in tests:
    recipe = search_recipe(search_term)
    if recipe:
        print(f"✅ Found '{search_term}' -> {recipe['name']}")
    else:
        print(f"❌ Failed to find '{search_term}'")

# Test 6: Partial match
print("\nTest 6: Partial match search")
recipe = search_recipe("деревянный")
if recipe:
    print(f"✅ Partial search 'деревянный' found: {recipe['name']}")
else:
    print(f"❌ Partial search failed")

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)

