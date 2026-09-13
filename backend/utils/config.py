"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Runtime settings for MediaMesh integrations."""

    tmdb_api_key: str | None = None
    google_api_key: str | None = None
    google_books_api_key: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    max_input_length: int = 20000
    database_url: str = ""


def load_settings() -> Settings:
    """Load settings from a local .env file and the process environment."""
    load_dotenv()
    return Settings(
        tmdb_api_key=os.getenv("TMDB_API_KEY"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        google_books_api_key=os.getenv("GOOGLE_BOOKS_API_KEY"),
        gemini_api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        max_input_length=int(os.getenv("MAX_INPUT_LENGTH", "20000")),
        database_url=os.getenv("DATABASE_URL", ""),
    )
