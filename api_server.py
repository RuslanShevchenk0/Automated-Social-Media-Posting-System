"""
FastAPI сервер для веб-інтерфейсу
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import logging
import asyncio
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

from scheduler import post_scheduler, analytics_collector
from api_routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Створюємо директорію для завантажень
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Запуск системи...")
    logger.info("📅 Запуск планувальника постів...")
    asyncio.create_task(post_scheduler.start())

    logger.info("📊 Запуск збирача аналітики (інтервал: 30 хв)...")
    asyncio.create_task(analytics_collector.start())

    logger.info("✅ Система готова до роботи")

    yield

    # Shutdown
    logger.info("🛑 Зупинка системи...")
    post_scheduler.stop()
    analytics_collector.stop()
    logger.info("✅ Систему зупинено")


app = FastAPI(title="Marketing Automation API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Підключаємо роутер з API endpoints
app.include_router(router, prefix="/api")

# ==================== СТАТИЧНІ ФАЙЛИ ====================

# Монтуємо статичні файли фронтенду
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def root():
    """Головна сторінка"""
    return FileResponse("frontend/index.html")


# ==================== ЗАПУСК ====================

if __name__ == "__main__":
    import uvicorn
    import sys

    # Налаштування для Windows консолі
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')

    print("="*70)
    print("Marketing Automation System")
    print("="*70)
    print("Web: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("="*70)

    uvicorn.run(app, host="0.0.0.0", port=8000)
