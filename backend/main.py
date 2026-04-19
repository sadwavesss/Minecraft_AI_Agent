import sys
import os
import subprocess
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.api.routes import router
from backend.api.routes import start_services, stop_services

OVERLAY_PROCESS = None

def launch_overlay_process():
    project_root = os.path.dirname(os.path.dirname(__file__))
    return subprocess.Popen(
        [sys.executable, "-m", "backend.overlay.window"],
        shell=False,
        cwd=project_root
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    global OVERLAY_PROCESS
    print("[INFO] Запуск сервера FastAPI...")
    print("[INFO] Запуск Overlay-окна...")
    OVERLAY_PROCESS = launch_overlay_process()

    print("[INFO] Инициализация захвата экрана и сервисов...")
    start_services()
    print("[SUCCESS] Все базовые сервисы запущены! Сервер готов.")
    
    yield
    
    print("[INFO] Остановка сервисов...")
    stop_services()
    
    if OVERLAY_PROCESS is not None:
        OVERLAY_PROCESS.terminate()
        OVERLAY_PROCESS.wait(timeout=2)
    print("[SUCCESS] Сервер успешно остановлен.")

app = FastAPI(title="Game Multimodal Assistant", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
