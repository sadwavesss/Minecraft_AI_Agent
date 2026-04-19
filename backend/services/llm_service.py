import os
from backend.services.tts_service import TTSManager
from backend.core.config import settings

tts_manager = TTSManager(speaker=settings.tts_speaker)

def speak_text(text: str):
    tts_manager.say(text)

def ask_gemini(question: str, image_bytes: bytes = None):
    try:
        import google.genai as genai
        from google.genai import types
    except ImportError:
        return "[gemini-unavailable] Пакет google-generativeai не установлен."

    api_key = settings.gemini_api_key
    
    if not api_key:
        return "[gemini-no-key] Не найден API ключ."
    client = genai.Client(api_key=api_key)

    system_instruction = (
        "Ты — мой ИИ-друг и помощник в играх. "
        "Ты анализируешь игровой экран, даешь советы, предлагаешь тактики, "
        "комментируешь происходящее, подбадриваешь и развлекаешь. "
        "Ты мощный АМ."
        "Обращай внимание только на игру и ее составляющие" 
        "Отвечай не более 150 символов и как человек избегая формальностей, будь живым и человечным в ответах "
        "Можешь использовать ненормативную лексику и сленг, если это уместно и соответствует твоему стилю общения"
        "Если нужно сказать какое-то слово которое используется только на латинице то пиши его на русском. Пример:(Dota=Дота)"
    )

    parts = [
        types.Part.from_text(text=f"System: {system_instruction}"),
        types.Part.from_text(text=f"User: {question}"),
    ]

    if image_bytes:
        try:
            parts.append(
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg",
                )
            )
        except Exception as err:
            return f"[gemini-error] Ошибка упаковки картинки: {err}"

    try:
        response = client.models.generate_content(
            model='gemini-flash-lite-latest',
            contents=[types.Content(role='user', parts=parts)],
        )
        answer = response.text
        speak_text(answer)
        return answer
    except Exception as e:
        return f"[gemini-error] {e}"
