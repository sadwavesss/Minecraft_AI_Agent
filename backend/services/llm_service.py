import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
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

class LLMService:
    """Сервис для взаимодействия с LLM (Gemini) через google.generativeai."""
    
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.is_configured = False
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.is_configured = True
            except Exception as e:
                print(f"[LLMService Error] Ошибка конфигурации Gemini API: {e}")

    def ask_gemini(self, question: str, image_bytes: bytes = None, history: list = None, system_prompt: str = None) -> str:
        """
        Отправляет мультимодальный запрос в Gemini с учетом истории диалога и заданного промпта.
        """
        if not self.is_configured:
            return "Ошибка: Неверный или отсутствующий ключ API Gemini."

        # Определяем активный характер и комбинируем с базовым правилом
        persona_prompt = system_prompt if system_prompt else PERSONAS.get("friendly", "")
        full_system_prompt = BASE_SYSTEM_PROMPT + persona_prompt
        
        # Настройка модели с системной инструкцией
        model = genai.GenerativeModel(
            "gemini-flash-lite-latest",
            system_instruction=full_system_prompt
        )
        
        contents = []

        # 1. Добавляем историю диалога (если есть)
        if history:
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [msg["content"]]})

        # 2. Текущий запрос
        current_parts = []
        if image_bytes:
            try:
                current_parts.append({"mime_type": "image/jpeg", "data": image_bytes})
            except Exception as err:
                return f"Ошибка упаковки изображения: {err}"
                
        current_parts.append(question)
        contents.append({"role": "user", "parts": current_parts})

        try:
            response = model.generate_content(contents)
            return response.text
        except Exception as e:
            print(f"[Gemini API Error] {e}")
            return "Произошла ошибка при обращении к сервису."
