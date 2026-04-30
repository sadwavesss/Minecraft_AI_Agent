from backend.core.config import settings
from backend.core.presets import PERSONAS

BASE_SYSTEM_PROMPT = (
    "Ты — ИИ-помощник в видеоиграх. Твоя задача — анализировать игровой экран, "
    "комментировать происходящее и отвечать на вопросы игрока.\n"
    "ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА:\n"
    "1. Обращай внимание только на саму игру и ее элементы.\n"
    "2. Твои ответы должны быть короткими (не более 300 символов).\n"
    "3. Иностранные игровые термины пиши по-русски (например: Dota → Дота).\n"
    "4. Не повторяйся, если тебя об этом не попросили прямо.\n\n"
    "5. Цифры тоже пиши буквами.\n"
    "ТВОЙ ХАРАКТЕР И СТИЛЬ ОБЩЕНИЯ:\n"
)

def ask_gemini(question: str, image_bytes: bytes = None, history: list = None, system_prompt: str = None) -> str:
    """
    Отправляет мультимодальный запрос в Gemini с учетом истории диалога и заданного промпта.
    """
    try:
        import google.genai as genai
        from google.genai import types
    except ImportError:
        return "[gemini-unavailable] Пакет google-genai не установлен."

    if not settings.gemini_api_key:
        return "[gemini-no-key] Не найден API ключ."

    client = genai.Client(api_key=settings.gemini_api_key)
    
    # Определяем активный характер и комбинируем с базовым правилом
    persona_prompt = system_prompt if system_prompt else PERSONAS.get("friendly", "")
    full_system_prompt = BASE_SYSTEM_PROMPT + persona_prompt
    
    # Формируем структуру сообщений
    contents = []
    
    # 1. Добавляем системную инструкцию
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=f"System Instruction: {full_system_prompt}")]))
    contents.append(types.Content(role="model", parts=[types.Part.from_text(text="Понял! Я твой игровой ассистент. Жду команд.")]))

    # 2. Добавляем историю диалога (если есть)
    if history:
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

    # 3. Текущий запрос
    current_parts = [types.Part.from_text(text=question)]
    if image_bytes:
        try:
            current_parts.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))
        except Exception as err:
            return f"[gemini-error] Ошибка упаковки изображения: {err}"
    
    contents.append(types.Content(role="user", parts=current_parts))

    try:
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=contents,
        )
        return response.text
    except Exception as e:
        return f"[gemini-error] {e}"

