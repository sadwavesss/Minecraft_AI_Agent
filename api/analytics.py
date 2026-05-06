from fastapi import APIRouter
from typing import Dict, Any
from api.catalog_labels import replace_resource_ids_with_labels
from api.markdown import render_markdown_to_html
from api.logs import logs_db
from api.advice import groq_client

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/session_summary")
async def get_session_summary() -> Dict[str, Any]:
    """Generate a post-match tactical analysis from the current session logs."""
    
    if not logs_db:
        return {"status": "error", "message": "Нет данных: логи пусты. Запустите игру и поиграйте немного!"}
        
    # Build session summary statistics
    deaths = sum(1 for log in logs_db if log.event_type == "death")
    low_health = sum(1 for log in logs_db if log.event_type == "low_health")
    hostiles = sum(1 for log in logs_db if log.event_type == "near_hostile")
    
    # Extract significant timeline
    timeline = []
    for log in logs_db:
        if log.event_type in ["death", "startup", "shutdown"]:
            timeline.append(f"[{log.event_type.upper()}] - {replace_resource_ids_with_labels(getattr(log, 'message', 'Событие'))}")
        elif log.event_type == "low_health" and (getattr(log, "player_health", 20) or 20) <= 6:
            timeline.append("[КРИТИЧЕСКОЕ ЗДОРОВЬЕ] - Здоровье упало до 6 или ниже")
            
    # Limit timeline to last 30 significant events to avoid context overflow
    if len(timeline) > 30:
        timeline = timeline[-30:]
        
    if not timeline:
        timeline.append("Ничего особо интересного не происходило.")
        
    session_summary = {
        "total_logs": len(logs_db),
        "deaths": deaths,
        "low_health_warnings": low_health,
        "hostile_encounters": hostiles,
        "timeline": timeline
    }
    
    if groq_client.is_available():
        analysis = await groq_client.generate_analytics_async(session_summary)
        if analysis:
            analysis_markdown = replace_resource_ids_with_labels(analysis)
            return {
                "status": "success",
                "analysis_markdown": analysis_markdown,
                "analysis_html": render_markdown_to_html(analysis_markdown),
                "stats": session_summary,
            }
            
    return {"status": "error", "message": "Не удалось сгенерировать аналитику. Проверьте ключ Groq API или сыграйте дольше."}
