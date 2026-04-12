# KP MC ASSISTANT — Документация для Copilot

> Этот файл создан для быстрого понимания кодовой базы в новых сессиях.

---

## Обзор проекта

AI-ассистент для Minecraft, работающий в реальном времени. Fabric-мод на Java перехватывает игровые события и чат игрока, отправляет их на локальный FastAPI-сервер, который формирует ответы через LLM (Groq API или Ollama) и отображает их в чате Minecraft.

---

## Архитектура

```
[Minecraft Client]
      |
   Fabric Mod (Java)
      |  POST /api/logs/         — игровые события (здоровье, смерть, ночь и т.д.)
      |  POST /api/rp/chat       — сообщения игрока из чата
      |  GET  /api/rp/           — периодический запрос RP-ответа (тиковый)
      |  GET  /api/settings/     — настройки интервалов
      v
   FastAPI Server (Python, port 8000)
      |
      |-- api/logs.py            — хранение событий в памяти (logs_db)
      |-- api/advice.py          — роутер /api/rp/, логика RP-ответов
      |-- api/groq_client.py     — обёртка над Groq API / Ollama
      |-- api/llm_config_manager.py — загрузка llm_config.json
      |-- api/settings.py        — настройки сервера
      |-- api/analytics.py       — послематчевая аналитика
      v
   LLM (Groq API или Ollama локально)
```

---

## Структура файлов

```
D:\KP MC ASSISTANT\
├── main.py                        — точка входа FastAPI, регистрирует роутеры
├── llm_config.json                — конфиг LLM: модели, параметры, промпты
├── settings.json                  — настройки сервера (интервалы, пороги)
├── requirements.txt               — Python зависимости
├── start_server.bat               — запуск FastAPI сервера (с логированием в logs/)
├── start_minecraft_client.bat     — запуск Minecraft через gradlew runClient (с логированием)
├── COPILOT_HELPER.md              — этот файл
│
├── api/
│   ├── advice.py                  — /api/rp/ роутер, вся RP-логика
│   ├── groq_client.py             — GroqClient: Groq API + Ollama (openai-совместимый)
│   ├── llm_config_manager.py      — загрузка/сохранение llm_config.json
│   ├── logs.py                    — /api/logs/ роутер, in-memory logs_db
│   ├── settings.py                — /api/settings/ роутер
│   └── analytics.py               — /api/analytics/ аналитика после сессии
│
├── models/
│   ├── groq_response.py           — GroqAdvice (ответ LLM), ChatMessage (сообщение игрока)
│   ├── llm_config.py              — Pydantic-модели: LLMConfig, ModelConfig, PromptsConfig
│   └── log_entry.py               — LogEntry (игровое событие), Settings
│
├── mod/minecraft-mod/
│   └── src/client/java/com/example/
│       ├── ExampleModClient.java         — точка входа мода, регистрация событий
│       ├── assistant/
│       │   ├── AssistantRuntime.java     — тиковая логика, отправка событий, sendChatMessage()
│       │   ├── HttpAssistantClient.java  — HTTP-клиент к FastAPI серверу
│       │   ├── AssistantConfig.java      — конфиг мода (URL, интервалы)
│       │   ├── ConfigManager.java        — загрузка/сохранение конфига мода
│       │   └── ChatMessageListener.java  — заглушка (не используется)
│       └── mixin/client/
│           ├── ExampleClientMixin.java   — заглушка Mixin на Minecraft.run()
│           └── ChatScreenMixin.java      — Mixin на ChatScreen.tick() (no-op)
│
├── logs/
│   ├── server.log                 — лог FastAPI сервера
│   └── minecraft_client.log       — лог Minecraft клиента
│
├── static/                        — HTML/JS/CSS для /admin панели
└── frontend/                      — доп. фронтенд-файлы
```

---

## Поток сообщений игрока (чат → LLM)

```
1. Игрок пишет в чат Minecraft
2. ExampleModClient.java → ClientSendMessageEvents.CHAT срабатывает
3. → AssistantRuntime.sendChatMessage(text) вызывается
4. → HttpAssistantClient.sendChat(text) → POST /api/rp/chat {"text": "..."}
5. → api/advice.py: player_chat_message() проверяет текст, вызывает groq_client
6. → GroqClient.generate_chat_response_async() → LLM API
7. → ответ возвращается в Java-мод
8. → отображается в чате через client.player.displayClientMessage()
```

**Важно**: до исправления (сессия 2026-03-15) `ClientSendMessageEvents.CHAT` не был зарегистрирован — `sendChatMessage()` никогда не вызывался. Исправлено в `ExampleModClient.java`.

---

## API Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/logs/` | Принять игровое событие от мода |
| GET | `/api/logs/` | Получить последние логи |
| WS | `/api/logs/ws` | WebSocket стрим логов в реальном времени |
| GET | `/api/rp/` | Получить RP-ответ на основе состояния игры |
| POST | `/api/rp/chat` | Отправить сообщение игрока, получить RP-ответ |
| GET | `/api/rp/history` | История ответов LLM (newest first, limit=100) |
| WS | `/api/rp/ws` | WebSocket стрим новых ответов в реальном времени |
| GET | `/api/rp/models/available` | Список доступных LLM моделей |
| POST | `/api/rp/models/switch` | Сменить активную модель |
| GET | `/api/settings/` | Получить настройки |
| POST | `/api/settings/` | Обновить настройки |
| GET | `/api/analytics/session_summary` | Получить сгенерированный LLM тактический отчет сессии |
| GET | `/admin` | Веб-панель администратора (логи) |
| GET | `/admin/responses` | Веб-панель ответов LLM (live) |
| GET | `/admin/analytics` | Веб-панель аналитики после матча |
| GET | `/admin/settings` | Веб-панель настроек |

---

## LLM Конфигурация (`llm_config.json`)

### Структура

```json
{
  "model_type": "llama",        // активная модель (ключ из models)
  "models": {
    "<ключ>": {
      "name": "...",            // имя модели для API
      "provider": "groq|ollama",// провайдер
      "description": "...",
      "parameters": {
        "max_tokens": 100,
        "temperature": 0.7,
        "reasoning_effort": "none"  // только для qwen через Groq
      }
    }
  },
  "prompts": {
    "state_based": "...",       // промпт для реакции на состояние игры, {context}
    "chat_based": "..."         // промпт для ответа на чат игрока, {player_message} и {context}
  }
}
```

### Провайдеры

| Провайдер | Требует | Как работает |
|-----------|---------|--------------|
| `groq` | `GROQ_API_KEY` в .env | Groq SDK (`from groq import Groq`) |
| `ollama` | Ollama запущен на `localhost:11434` | OpenAI-совместимый API (`openai` пакет) |

### Добавление новой модели

1. Добавить запись в `llm_config.json` → `models`
2. Если новый провайдер — добавить обработку в `api/groq_client.py` (метод `__init__`)
3. Сменить модель через POST `/api/rp/models/switch?model_type=<ключ>` или изменить `model_type` в `llm_config.json`

---

## GroqClient (`api/groq_client.py`)

Класс поддерживает два провайдера:
- **Groq**: инициализируется через `Groq(api_key=...)`, требует `GROQ_API_KEY`
- **Ollama**: инициализируется через `OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")`, API ключ не нужен

Метод `is_available()`:
- Для Groq: `client is not None and api_key is not None`
- Для Ollama: `client is not None` (API ключ не требуется)

Асинхронные методы (`generate_tip_async`, `generate_chat_response_async`) оборачивают блокирующие вызовы через `ThreadPoolExecutor`.

---

## Игровые события (event_type)

| Событие | Когда | Данные |
|---------|-------|--------|
| `startup` | При подключении мода | health, food |
| `state` | Каждые N тиков | health, food |
| `low_health` | health ≤ 6.0 (раз в ~10с) | health, food |
| `hunger_low` | food ≤ 8 (раз в ~15с) | food, health |
| `night` | Переход день→ночь (раз в ~60с) | time |
| `near_hostile` | Враги в радиусе 14 блоков (раз в ~5с) | count, radius, types |
| `death` | Смерть игрока (кулдаун 60с) | cause |

---

## Rate Limiting RP-ответов

- `_min_interval_seconds = 20` — минимум 20 секунд между рутинными RP-ответами
- Критические события (`death`) обходят rate limiting
- `_has_situation_changed()` — не отправляет ответ если ситуация не изменилась

---

## Тестирование

1. Запустить сервер: `start_server.bat` (порт 8000)
2. Запустить клиент: `start_minecraft_client.bat` (Fabric dev client)
3. Логи пишутся в `logs/server.log` и `logs/minecraft_client.log`
4. Веб-панель: http://127.0.0.1:8000/admin
5. Переменные окружения: `GROQ_API_KEY` в файле `.env` в корне проекта

### Проверка чата

В игре написать любое сообщение в чат → в консоли сервера должно появиться:
```
[AI Assistant API] /api/rp/chat called with: <текст>
[AI Assistant API] LLM response: <ответ>
```

---

## Известные баги / Исправления

| Дата | Баг | Файл | Исправление |
|------|-----|------|-------------|
| 2026-03-15 | Сообщения игрока не доходили до LLM | `ExampleModClient.java` | Добавлен `ClientSendMessageEvents.CHAT.register(...)` |
| 2026-03-15 | `ChatScreenMixin.onTick` спамил консоль каждый тик | `ChatScreenMixin.java` | Убран `System.out.println` |
| 2026-03-15 | Ответ на чат не отображался в Minecraft | `AssistantRuntime.java` | Добавлен `mc.player.displayClientMessage(...)` в `sendChatMessage()` |
| 2026-03-15 | `<think>...</think>` теги Qwen3 утекали в ответ | `groq_client.py` | Добавлен `_strip_thinking()` с `re.sub` |
| 2026-03-15 | `GET /api/rp/` таймаут при долгом ответе LLM | `HttpAssistantClient.java` | Таймаут увеличен с 5 до 15 сек |
| 2026-03-15 | `GET /api/rp/chat` таймаут для локальной модели | `HttpAssistantClient.java` | Таймаут увеличен с 5 до 30 сек |

---

## Зависимости

```
fastapi>=0.110
uvicorn[standard]>=0.27
pydantic>=2.6
groq>=0.5.0
openai>=1.0.0          # для Ollama (OpenAI-совместимый API)
python-dotenv>=1.0.0
```

---

## Переменные окружения (`.env`)

```
GROQ_API_KEY=gsk_...   # API ключ Groq (не нужен если используется только Ollama)
```
