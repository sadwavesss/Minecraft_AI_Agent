from fastapi import APIRouter
from typing import Dict, Any, Optional
from api.advice import groq_client

router = APIRouter(prefix="/api/wiki", tags=["wiki"])

@router.get("/craft")
async def search_craft(query: Optional[str] = None) -> Dict[str, Any]:
    """Search for a crafting recipe using LLM."""
    if not query or len(query.strip()) == 0:
        return {"status": "error", "message": "Пустой запрос."}
        
    if not groq_client.is_available():
        return {"status": "error", "message": "Groq LLM недоступен. Проверьте API ключ."}
        
    recipe = await groq_client.search_crafting_recipe_async(query)
    
    if recipe:
        return {"status": "success", "recipe": recipe}
    else:
        return {"status": "error", "message": "Не удалось сгенерировать рецепт или произошла ошибка LLM."}
