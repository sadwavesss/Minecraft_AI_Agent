import threading
import time
import numpy as np
import pyaudio
from faster_whisper import WhisperModel
from backend.core.config import settings

class VoiceListener:
    def __init__(self, model_name=None, device=None, threshold=0.02, silence_duration=0.5):
        self.model_name = model_name or settings.whisper_model
        self.device = device or settings.whisper_device
        self.model = None
        self.model_loaded = False
        
        self.threshold = threshold
        self.silence_duration = silence_duration
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_listening = False
        self.on_transcription = None
        
        # Загружаем модель в фоновом потоке, чтобы не блокировать запуск программы
        threading.Thread(target=self._init_model, daemon=True).start()

    def _init_model(self):
        print("[INFO] Начинается фоновая загрузка голосовой модели (faster-whisper)...")
        # 1. Смена модели на "base" (в 3 раза быстрее small)
        # 2. compute_type="int8" (критично для CPU, ускоряет в 2-3 раза)
        # 3. cpu_threads=4 (используем больше ядер)
        self.model = WhisperModel(
            self.model_name, 
            device=self.device, 
            compute_type="int8", 
            cpu_threads=4, 
            num_workers=2
        )
        self.model_loaded = True
        print("[SUCCESS] Голосовая модель (faster-whisper) успешно загружена и готова к работе!")

    def start(self):
        if self.is_listening:
            return
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            self.is_listening = True
            print("[INFO] Микрофон активирован. Слушаю...")
            threading.Thread(target=self._listen_loop, daemon=True).start()
        except Exception as e:
            print(f"[ERROR] Не удалось активировать микрофон: {e}")
            self.is_listening = False

    def stop(self):
        self.is_listening = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        print("[INFO] Микрофон остановлен.")

    def _listen_loop(self):
        buffer = []
        silence_start = None
        recording_started = False
        
        while self.is_listening:
            data = self.stream.read(1024, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            audio_data = audio_data * 1.5
            rms = np.sqrt(np.mean(audio_data**2))

            if rms > self.threshold:
                buffer.extend(audio_data)
                silence_start = None
                recording_started = True
            else:
                if recording_started:
                    if silence_start is None:
                        silence_start = time.time()
                    
                    if time.time() - silence_start > self.silence_duration:
                        # Сократили минимальный порог накопления для более быстрой реакции
                        if len(buffer) > 4000: 
                            audio_np = np.array(buffer)
                            
                            # САМЫЙ ВАЖНЫЙ БЛОК ДЛЯ СКОРОСТИ
                            if not self.model_loaded:
                                print("[WAIT] Модель всё ещё загружается, подождите немного...")
                            else:
                                segments, _ = self.model.transcribe(
                                    audio_np, 
                                    language="ru", 
                                    beam_size=5,        # 1 вместо 5 (ускорение в 5 раз)
                                    best_of=1,          # Не перебирать варианты
                                    vad_filter=True,    # Внутренний VAD для очистки мусора
                                    initial_prompt="Игровой помощник. Кратко." # Помогает базе не тупить
                                )
                                
                                text = " ".join([seg.text for seg in segments]).strip()
                                if text and self.on_transcription:
                                    self.on_transcription(text)
                        
                        buffer = []
                        recording_started = False
                        silence_start = None
                else:
                    buffer = []
class WhisperService:
    def __init__(self, model_name=None, device=None):
        self.model = WhisperModel(
            model_name or settings.whisper_model, 
            device=device or settings.whisper_device
        )

    def transcribe_file(self, filename: str):
        segments, _ = self.model.transcribe(filename)
        return " ".join([segment.text for segment in segments])
