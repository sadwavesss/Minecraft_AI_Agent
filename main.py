from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from api import logs, settings
from api import advice
from api.llm_config_manager import get_llm_config

app = FastAPI(title="AI Assistant Admin")

# Initialize LLM config
llm_config = get_llm_config()
print(f"[LLM Config] Loaded model: {llm_config.model_type}")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print("[VALIDATION ERROR]", request.method, request.url)
    print(exc.errors())
    try:
        print("[VALIDATION ERROR BODY]", exc.body)
    except Exception:
        pass
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

# Подключение роутеров
app.include_router(logs.router)
app.include_router(settings.router)
app.include_router(advice.router)

# Статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

BASE_DIR = Path(__file__).resolve().parent


@app.get("/admin")
async def admin_logs_page():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/admin/settings")
async def admin_settings_page():
    return FileResponse(BASE_DIR / "static" / "settings.html")

@app.get("/")
async def root():
    return {"message": "Admin panel at /admin"}
