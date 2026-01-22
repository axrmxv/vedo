from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения"""
    
    # Основные настройки
    PROJECT_NAME: str = "Vedo Calculator"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Безопасность
    SECRET_KEY: str = "your"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    
    # База данных
    DATABASE_URL: str = "sqlite+aiosqlite:///./vedo.db"
    
    # Администратор по умолчанию
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "Hd7s9v3rE"
    
    # Файлы
    STORAGE_PATH: str = "../storage"
    MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20 МБ
    FILE_RETENTION_DAYS: int = 7
    
    # Логирование
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "../logs/app.log"
    
    # Константы обработки
    FORM_CAPACITY_1: int = 15
    FORM_CAPACITY_2: int = 20
    FORM_CAPACITY_3: int = 10
    CUTOFF_TYPE_1: int = 8
    CUTOFF_TYPE_2: int = 9
    CUTOFF_TYPE_3: int = 10
    
    # CORS (для разработки)
    BACKEND_CORS_ORIGINS: list = ["http://localhost", "http://localhost:8035"]
    
    # Окружение
    ENVIRONMENT: Literal["development", "production"] = "production"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
