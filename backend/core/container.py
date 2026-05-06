import asyncio
from typing import Optional

from backend.core.capture import ScreenCapture
from backend.core.vision import preprocess_frame
from backend.core.voice import VoiceListener
from backend.services.memory_service import MemoryService
from backend.services.pipeline import RequestPipeline
from backend.services.llm_service import LLMService
from backend.services.tts_service import TTSManager

class ApplicationContainer:
    """
    Центральный IoC-контейнер приложения.
    Владеет жизненным циклом всех подсистем и координирует их взаимодействие.
    """

    def __init__(self):
        self.capture = ScreenCapture(fps=12)
        self.voice_listener = VoiceListener()
        self.memory_service = MemoryService()
        self.llm_service = LLMService()
        self.tts_manager = TTSManager()
        self.current_overlay_text: str = ""
        self.current_overlay_status: str = "IDLE"
        self.is_active = False
        self.overlay_visible = True
        self.settings_persona: str = "friendly"
        self.settings_voice: str = "baya"
        self.settings_show_subtitles: bool = True
        self.settings_volume: float = 1.0
        self.settings_show_visualizer: bool = True
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None

        self.pipeline = RequestPipeline(
            overlay_callback=self._on_pipeline_response,
            memory_service=self.memory_service,
            tts_manager=self.tts_manager,
            llm_service=self.llm_service,
            get_settings_callback=self._get_pipeline_settings
        )

        self.voice_listener.on_transcription = self._on_voice_transcription

    def _get_pipeline_settings(self) -> dict:
        return {
            "persona": self.settings_persona,
            "voice": self.settings_voice,
            "volume": self.settings_volume
        }

    def _on_pipeline_response(self, text: str) -> None:
        """Вызывается pipeline'ом при получении ответа от Gemini."""
        self.current_overlay_text = text
        self.current_overlay_status = "IDLE"
        print(f"[PIPELINE] Ответ для оверлея: {text}")

    def _is_cancel_command(self, text: str) -> bool:
        """Проверяет, является ли текст командой отмены (короткая фраза со стоп-словом)."""
        cancel_words = {"тихо", "замолчи", "стоп", "хватит", "заткнись", "молчи", "молчать"}
        
        import string
        # Очищаем от пунктуации и переводим в нижний регистр
        clean_text = text.lower().translate(str.maketrans('', '', string.punctuation))
        words = clean_text.split()
        
        return len(words) <= 3 and any(word in cancel_words for word in words)

    def _on_voice_transcription(self, text: str) -> None:
        """Вызывается VoiceListener после транскрибации речи."""
        try:
            print(f"🎤 Транскрибация: {text}")
            
            # Прерываем только если фраза короткая и содержит ключевое слово
            if self._is_cancel_command(text):
                print("[INFO] Распознана короткая команда отмены. Останавливаем TTS и очищаем очередь.")
                self.tts_manager.stop_playback()
                
                if self._main_loop is not None:
                    self._main_loop.call_soon_threadsafe(self.pipeline.clear_queue)
                    
                self.current_overlay_text = "..."
                self.current_overlay_status = "IDLE"
                return

            frame = self.capture.get_frame()
            image_bytes = preprocess_frame(frame) if frame is not None else None
            frames_buffer = self.capture.get_frame_buffer()

            if self._main_loop is None:
                print("[ERROR] Main event loop не инициализирован в контейнере!")
                return

            asyncio.run_coroutine_threadsafe(
                self.pipeline.add_request(text, image_bytes, frames_buffer),
                loop=self._main_loop,
            )
        except Exception as e:
            print(f"[ERROR] Ошибка при обработке транскрипции: {e}")

    def set_overlay_status(self, status: str) -> None:
        """Обновляет статусное сообщение для PTT-индикатора в оверлее."""
        self.current_overlay_status = status

    def start_all(self) -> None:
        # asyncio.get_running_loop() возбуждает RuntimeError, если loop не запущен.
        # В контексте FastAPI lifespan он всегда запущен — используем напрямую.
        self._main_loop = asyncio.get_running_loop()

        self.capture.start()
        self.voice_listener.start()
        self.pipeline.start()
        print("[INFO] Core services (Capture, Voice, Pipeline) started.")

    def stop_all(self) -> None:
        self.capture.stop()
        self.voice_listener.stop()
        self.pipeline.stop()
        print("[INFO] Core services stopped.")


container = ApplicationContainer()
