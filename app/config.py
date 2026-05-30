"""Centralised application configuration loaded from environment variables.

Uses pydantic-settings so every setting is validated and typed. Nothing
secret is hard-coded — values come from the environment / .env file.
"""
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ----- App -----
    app_name: str = "Vocal Vantage"
    environment: str = Field(default="development")  # development | production
    debug: bool = Field(default=True)
    secret_key: str = Field(default="change-me-in-production")

    # ----- Database -----
    # Example: postgresql+asyncpg://user:pass@host:5432/vocal_vantage
    database_url: str = Field(
        default="sqlite+aiosqlite:///./vocal_vantage.db"
    )

    # ----- Redis -----
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_enabled: bool = Field(default=True)

    # ----- JWT / Auth -----
    jwt_secret_key: str = Field(default="jwt-change-me-in-production")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60 * 24)  # 1 day

    # ----- AI providers -----
        # ----- AI providers -----
    # Transcription provider: "groq" (free) | "openai" (paid) | "auto"
    transcription_provider: str = Field(default="auto")

    openai_api_key: str = Field(default="")
    openai_whisper_model: str = Field(default="whisper-1")

    # Groq offers Whisper transcription on a generous free tier.
    groq_api_key: str = Field(default="")
    groq_whisper_model: str = Field(default="whisper-large-v3-turbo")

    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-1.5-flash")

    # Allow running without paid APIs: when true, deterministic mock
    # transcripts/feedback are returned so the full pipeline is demoable.
    ai_mock_mode: bool = Field(default=False)

    # ----- Uploads -----
    max_upload_mb: int = Field(default=25)
    allowed_audio_extensions: str = Field(
        default="mp3,wav,m4a,webm,ogg,flac,mp4,mpeg,mpga"
    )

    # ----- Rate limiting (per IP / user, per window) -----
    rate_limit_requests: int = Field(default=20)
    rate_limit_window_seconds: int = Field(default=60)

    # ----- CORS -----
    cors_origins: str = Field(default="*")

    @field_validator("environment")
    @classmethod
    def _normalise_env(cls, v: str) -> str:
        return v.lower().strip()

    @property
    def allowed_extensions_set(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_audio_extensions.split(",") if e.strip()}

    @property
    def cors_origin_list(self) -> List[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
