from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel

from backend.core.container import container
from backend.core.vision import preprocess_frame
from backend.core.presets import PERSONAS, VOICES

router = APIRouter()

class SettingsUpdate(BaseModel):
    persona: str | None = None
    voice: str | None = None
    show_subtitles: bool | None = None
    volume: float | None = None
    show_visualizer: bool | None = None

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/latest_response")
def get_latest_response():
    return {"answer": container.current_overlay_text}

@router.get("/status")
def get_status():
    """Возвращает текущий статус системы для оверлея."""
    return {
        "status": container.current_overlay_status,
        "visible": container.overlay_visible,
        "show_subtitles": container.settings_show_subtitles,
        "show_visualizer": container.settings_show_visualizer
    }

@router.get("/settings/meta")
def get_settings_meta():
    return {
        "personas": list(PERSONAS.keys()),
        "voices": VOICES
    }

@router.get("/settings")
def get_settings():
    return {
        "persona": container.settings_persona,
        "voice": container.settings_voice,
        "show_subtitles": container.settings_show_subtitles,
        "volume": container.settings_volume,
        "show_visualizer": container.settings_show_visualizer
    }

@router.post("/settings")
def update_settings(settings: SettingsUpdate):
    if settings.persona is not None:
        container.settings_persona = settings.persona
    if settings.voice is not None:
        container.settings_voice = settings.voice
    if settings.show_subtitles is not None:
        container.settings_show_subtitles = settings.show_subtitles
    if settings.volume is not None:
        container.settings_volume = settings.volume
    if settings.show_visualizer is not None:
        container.settings_show_visualizer = settings.show_visualizer
    return {"status": "settings updated"}


@router.post("/start")
async def start_all():
    container.memory_service.clear_session()
    container.start_all()
    container.is_active = True
    return {"status": "all core services started and memory cleared"}


@router.post("/stop")
def stop_all():
    container.stop_all()
    return {"status": "all core services stopped"}


@router.post("/ask")
async def ask(question: str = Form(...), include_frame: bool = Form(False)):
    image_bytes = None
    if include_frame:
        frame = container.capture.get_frame()
        if frame is not None:
            image_bytes = preprocess_frame(frame)

    await container.pipeline.add_request(question, image_bytes)
    return {"status": "request added to pipeline"}

