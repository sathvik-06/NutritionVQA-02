"""Application settings (OCR-only, no RAG)."""
import os
from dotenv import load_dotenv

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_PROJECT = os.path.abspath(os.path.join(_BACKEND, ".."))
load_dotenv(os.path.join(_PROJECT, ".env"), override=True)


def _upload_dir() -> str:
    raw = os.getenv("UPLOAD_DIR", os.path.join(_BACKEND, "uploads"))
    if not os.path.isabs(raw):
        raw = os.path.join(_BACKEND, raw)
    return os.path.abspath(raw)


class Settings:
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "nutritionvqa")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "open-mistral-7b")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))
    UPLOAD_DIR: str = _upload_dir()
    BACKEND_DIR: str = _BACKEND
    PROJECT_ROOT: str = _PROJECT
    MAX_FILE_SIZE: int = 10 * 1024 * 1024
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "")


settings = Settings()
