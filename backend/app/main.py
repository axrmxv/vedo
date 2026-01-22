from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from app.core.config import settings
from app.core.database import init_db
from app.api.routes import auth, files, admin
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.init_admin import init_default_admin


# Настройка логирования
def setup_logging():
    """Настройка логирования приложения"""
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Формат логов
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Файловый handler с ротацией (10 МБ, 5 файлов)
    file_handler = RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.INFO)
    
    # Консольный handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.INFO)
    
    # Корневой logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения
    
    Args:
        app: Экземпляр FastAPI
    """
    # Startup
    logger.info("Запуск приложения...")
    
    # Создание необходимых директорий
    Path(settings.STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    
    # Инициализация БД
    await init_db()
    logger.info("База данных инициализирована")
    
    # Создание администратора по умолчанию
    await init_default_admin()
    
    # Запуск планировщика задач
    start_scheduler()
    logger.info("Планировщик задач запущен")
    
    logger.info("Приложение запущено успешно")
    
    yield
    
    # Shutdown
    logger.info("Остановка приложения...")
    stop_scheduler()
    logger.info("Приложение остановлено")


# Создание FastAPI приложения
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(files.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)

# Статические файлы (frontend)
app.mount("/static", StaticFiles(directory="../static"), name="static")

# Главная страница (HTML)
@app.get("/")
async def root():
    """Отдача главной HTML страницы"""
    from fastapi.responses import FileResponse
    return FileResponse("../static/index.html")


@app.get("/health")
async def health_check():
    """Проверка работоспособности"""
    return {"status": "healthy", "version": settings.VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="localhost",
        port=8035,
        reload=settings.ENVIRONMENT == "development"
    )
