# Minecraft AI Assistant (FastAPI + Fabric client mod)

Проект состоит из двух частей:

- **FastAPI сервер** (логи, настройки, выдача советов)
- **Fabric client-only мод** (сбор событий из игры, отправка логов на сервер, показ советов в игре)

## Структура

- `main.py` — FastAPI приложение
- `api/` — роуты (`/api/logs`, `/api/settings`, `/api/advice`)
- `models/` — Pydantic модели
- `static/` — HTML страницы админки
- `frontend/` — JS для админки
- `mod/minecraft-mod/` — исходники Fabric мода (Java 17, Minecraft 1.20.1)

## Требования

### Для сервера

- Python **3.11+**

### Для мода

- Java **17**
- Gradle wrapper (в проекте уже есть)

## Быстрый старт (сервер)

1) Создать и активировать виртуальное окружение:

```powershell
python -m venv venv
.\venv\Scripts\activate
```

2) Поставить зависимости:

```powershell
pip install -r requirements.txt
```

3) Запустить сервер:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

4) Открыть админку:

- `http://127.0.0.1:8000/admin`
- `http://127.0.0.1:8000/admin/settings`

## Быстрый старт (Minecraft мод)

1) Перейти в папку мода:

```powershell
cd mod\minecraft-mod
```

2) Запустить dev-клиент:

```powershell
.\gradlew.bat runClient
```

Мод (клиентский) будет:

- отправлять `POST /api/logs/` на сервер
- периодически получать советы с `GET /api/advice/`
- показывать советы в игре (actionbar)

## Настройки

### Настройки сервера (админка)

Настройки редактируются на странице `http://127.0.0.1:8000/admin/settings` и сохраняются в `settings.json`.

Важно:

- `analysis_interval` (мс) — влияет на частоту отправки `state` логов из мода (например `5000` = раз в 5 секунд)
- `threat_threshold` — влияет на правило в `/api/advice/`

### Настройки мода

В моде есть конфиг (Fabric config dir) `ai_assistant.json` (создаётся автоматически), где задаются:

- `serverUrl` (по умолчанию `http://127.0.0.1:8000`)
- интервалы (fallback), если сервер недоступен

## MVP события

Мод отправляет события в формате:

- `event_type` — тип события
- `event_data` — данные

MVP события (6 шт):

- `startup`
- `state`
- `low_health`
- `hunger_low`
- `night`
- `near_hostile`

## Нюансы для команды

- **Не коммитить** `venv/`, `mod/minecraft-mod/run/`, `build/` — они в `.gitignore`.
- Если кто-то запускает сервер не на своей машине, то в конфиге мода нужно указать `serverUrl` на реальный IP/домен сервера (не `127.0.0.1`).
- Убедитесь, что у вас **Java 17** (иначе Fabric/Gradle сборка сломается).
