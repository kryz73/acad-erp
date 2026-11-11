import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # Application settings automatically loaded from environment variables or a .keys file.
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256" 
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000,http://localhost:5432"

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".keys"), env_file_encoding="utf-8", extra = "ignore")

settings = Settings()