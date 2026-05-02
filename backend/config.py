"""
Centralised settings — reads from .env automatically.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM
    GROQ_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # ASR
    HF_API_TOKEN: str = ""
    HF_INDIC_WHISPER_URL: str = (
        "https://api-inference.huggingface.co/models/vasista22/whisper-kannada-medium"
    )
    HF_WHISPER_FALLBACK_URL: str = (
        "https://api-inference.huggingface.co/models/openai/whisper-large-v3"
    )

    # TTS
    BHASHINI_API_KEY: str = ""
    BHASHINI_USER_ID: str = ""

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Redis
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""

    # App
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = ""
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
