import os
import base64
from fastapi import APIRouter, HTTPException, Form
from backend.core.capture import ScreenCapture
from backend.core.vision import preprocess_frame
from backend.core.voice import VoiceListener
from backend.services.llm_service import ask_gemini

router = APIRouter()

capture = ScreenCapture(fps=12)
voice_listener = VoiceListener()

def start_services():
    # Мы больше не запускаем сервисы автоматически здесь,
    # чтобы пользователь мог запустить их кнопкой из оверлея
    pass

def stop_services():
    capture.stop()
    voice_listener.stop()

def on_voice_transcription(text: str):
    """Callback при транскрибации голоса."""
    print(f"🎤 Транскрибация: {text}")
    frame = capture.get_frame()
    if frame is not None:
        jpg = preprocess_frame(frame)
        answer = ask_gemini(text, jpg)
        print(f"🤖 Ответ: {answer}")
    else:
        print("❌ Кадр не готов")

voice_listener.on_transcription = on_voice_transcription

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/frame")
def get_frame():
    frame = capture.get_frame()
    if frame is None:
        raise HTTPException(status_code=503, detail="Frame не готов")
    jpg = preprocess_frame(frame)
    if jpg is None:
        raise HTTPException(status_code=500, detail="Frame обработка не удалась")
    return {"frame": base64.b64encode(jpg).decode("utf-8")}

@router.post("/start")
def start_all():
    capture.start()
    voice_listener.start()
    return {"status": "all services started"}

@router.post("/stop")
def stop_all():
    capture.stop()
    voice_listener.stop()
    return {"status": "all services stopped"}

@router.post("/voice/start")
def start_voice():
    voice_listener.start()
    return {"status": "voice listening started"}

@router.post("/voice/stop")
def stop_voice():
    voice_listener.stop()
    return {"status": "voice listening stopped"}

@router.post("/ask")
def ask(question: str = Form(...), include_frame: bool = Form(False)):
    image_bytes = None
    if include_frame:
        frame = capture.get_frame()
        if frame is not None:
            image_bytes = preprocess_frame(frame)
    answer = ask_gemini(question, image_bytes)
    return {"question": question, "answer": answer}
