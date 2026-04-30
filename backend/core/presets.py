import os
import json

PRESETS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "presets.json")

def load_presets():
    try:
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("personas", {}), data.get("voices", [])
    except Exception as e:
        print(f"[ERROR] Не удалось загрузить пресеты: {e}")
        # Возвращаем дефолтные значения если файла нет
        return {"friendly": "Ты — мой ИИ-друг и помощник в играх. Будь краток."}, ["aidar", "baya"]

PERSONAS, VOICES = load_presets()

def save_presets(personas, voices):
    try:
        os.makedirs(os.path.dirname(PRESETS_FILE), exist_ok=True)
        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump({"personas": personas, "voices": voices}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] Не удалось сохранить пресеты: {e}")
