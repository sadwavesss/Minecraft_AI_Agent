import asyncio
import time
import os
from dataclasses import dataclass, field
from typing import Optional, Callable

from backend.services.llm_service import LLMService
from backend.services.tts_service import TTSManager
from backend.services.memory_service import MemoryService


@dataclass
class UserRequest:
    text: str
    image_bytes: Optional[bytes] = None
    frames_buffer: Optional[list] = None
    timestamp: float = field(default_factory=time.time)


class RequestPipeline:
    """
    FIFO-конвейер обработки запросов (Producer-Consumer).
    Гарантирует порядок вывода ответов через asyncio.Queue.
    Оверлей и TTS запускаются параллельно согласно ТЗ.
    """

    def __init__(
        self, 
        overlay_callback: Callable[[str], None], 
        memory_service: MemoryService,
        tts_manager: TTSManager,
        llm_service: LLMService,
        get_settings_callback: Callable[[], dict]
    ):
        self.queue: asyncio.Queue[UserRequest] = asyncio.Queue()
        self.overlay_callback = overlay_callback
        self.memory_service = memory_service
        self.tts_manager = tts_manager
        self.llm_service = llm_service
        self.get_settings_callback = get_settings_callback
        self.is_running = False
        self._worker_task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if not self.is_running:
            self.is_running = True
            self._worker_task = asyncio.create_task(self._worker())
            print("[INFO] Pipeline worker started.")

    def stop(self) -> None:
        self.is_running = False
        if self._worker_task:
            self._worker_task.cancel()
            print("[INFO] Pipeline worker stopped.")

    async def add_request(self, text: str, image_bytes: Optional[bytes] = None, frames_buffer: Optional[list] = None) -> None:
        request = UserRequest(text=text, image_bytes=image_bytes, frames_buffer=frames_buffer)
        await self.queue.put(request)

    def clear_queue(self) -> None:
        """Очищает очередь невыполненных запросов."""
        try:
            while not self.queue.empty():
                self.queue.get_nowait()
                self.queue.task_done()
        except Exception as e:
            print(f"[WARNING] Ошибка при очистке очереди: {e}")
        print("[INFO] Pipeline queue cleared.")

    async def _worker(self) -> None:
        loop = asyncio.get_running_loop()

        while self.is_running:
            try:
                request = await self.queue.get()

                # 1. Получаем последние сообщения из памяти для контекста (Dialogue Flow)
                history = self.memory_service.get_recent_history(limit=5)

                # Получаем текущие настройки из контейнера
                from backend.core.presets import PERSONAS
                
                settings = self.get_settings_callback()
                sys_prompt = PERSONAS.get(settings.get("persona", "friendly"), PERSONAS["friendly"])
                self.tts_manager.set_speaker(settings.get("voice", "baya"))
                self.tts_manager.set_volume(settings.get("volume", 1.0))

                # 3. Запрос к Gemini (sync → async через executor)
                answer = await loop.run_in_executor(
                    None, self.llm_service.ask_gemini, request.text, request.image_bytes, history, sys_prompt
                )

                if answer:
                    # 4. Сохраняем диалог в память
                    self.memory_service.add_message("user", request.text)
                    self.memory_service.add_message("assistant", answer)

                    # 5. Вывод в оверлей и TTS запускаются ПАРАЛЛЕЛЬНО (требование ТЗ)
                    await asyncio.gather(
                        loop.run_in_executor(None, self.overlay_callback, answer),
                        loop.run_in_executor(None, self.tts_manager.say, answer),
                    )

                self.queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ERROR] Pipeline error: {e}")
                await asyncio.sleep(1)