import torch
import sounddevice as sd
import time
import threading
from queue import Queue
from backend.core.config import settings

class TTSManager:
    def __init__(self, model_id=None, speaker=None, device=None, sample_rate=None):
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.speaker = speaker or settings.tts_speaker
        self.sample_rate = sample_rate or settings.tts_sample_rate
        self.model_id = model_id or settings.tts_model_id
        self.text_queue = Queue()
        self.model = None
        
        # Запускаем поток обработки очереди
        threading.Thread(target=self._worker, daemon=True).start()

    def _init_model(self):
        if self.model is None:
            print(f"--- Инициализация Silero на {self.device} ---")
            self.model, _ = torch.hub.load(repo_or_dir='snakers4/silero-models',
                                          model='silero_tts',
                                          language='ru',
                                          speaker=self.model_id,
                                          trust_repo=True)
            self.model.to(self.device)

    def say(self, text: str):
        """Добавляет текст в очередь на озвучку"""
        if text:
            self.text_queue.put(text)

    def _worker(self):
        """Фоновый процесс: берет текст из очереди и озвучивает"""
        self._init_model()
        while True:
            text = self.text_queue.get()
            try:
                # Очистка текста от лишних символов для стабильности
                clean_text = text.replace('\n', ' ').strip()
                
                # Ускоряем чтение на 20% через SSML теги
                ssml_text = f"<prosody rate='1.5'>{clean_text}</prosody>"
                
                audio = self.model.apply_tts(text=ssml_text,
                                            speaker=self.speaker,
                                            sample_rate=self.sample_rate)
                
                sd.play(audio.cpu().numpy(), self.sample_rate)
                sd.wait() # Ждем, пока договорит, прежде чем брать следующий текст
            except Exception as e:
                print(f"[TTS Worker Error] {e}")
            finally:
                self.text_queue.task_done()