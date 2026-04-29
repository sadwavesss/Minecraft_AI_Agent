from fastapi import APIRouter
from typing import Dict, Any, Optional
from api.minecraft_recipes import search_recipe, validate_recipe_grid
from api.advice import groq_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/wiki", tags=["wiki"])

@router.get("/craft")
async def search_craft(query: Optional[str] = None) -> Dict[str, Any]:
    """Search for a crafting recipe from database or LLM."""
    if not query or len(query.strip()) == 0:
        return {"status": "error", "message": "Пустой запрос."}
    
    # Сначала проверяем локальную базу данных
    recipe = search_recipe(query)
    if recipe:
        # Убедитесь что сетка валидна
        if validate_recipe_grid(recipe.get("grid", [])):
            logger.info(f"Found recipe in database: {query}")
            return {"status": "success", "recipe": recipe}
    
    # Если не найдено в БД - используем LLM как fallback
    if not groq_client.is_available():
        return {"status": "error", "message": "Рецепт не найден. LLM недоступен."}
    
    try:
        llm_recipe = await groq_client.search_crafting_recipe_async(query)
        
        if llm_recipe and validate_recipe_grid(llm_recipe.get("grid", [])):
            logger.info(f"Generated recipe via LLM: {query}")
            return {"status": "success", "recipe": llm_recipe}
        else:
            return {"status": "error", "message": f"Рецепт для '{query}' не найден или не может быть скрафчен."}
    except Exception as e:
        logger.error(f"Error generating recipe: {e}")
        return {"status": "error", "message": "Ошибка при поиске рецепта."}
