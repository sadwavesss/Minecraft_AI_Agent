from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

import logging

class EndpointFilter(logging.Filter):
    """Фильтр для очистки логов от частых запросов оверлея."""
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "/api/latest_response" not in msg and "/api/status" not in msg

class Settings(BaseSettings):
    # Gemini API Key
    gemini_api_key: str 
    
    # Whisper (Voice Transcription) Settings
    whisper_model: str
    whisper_device: str
    
    # TTS (Text to Speech) Settings
    tts_model_id: str
    tts_speaker: str
    tts_sample_rate: int
    tts_speed: float

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
