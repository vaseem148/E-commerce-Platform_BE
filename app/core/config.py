"""Application configuration powered by pydantic-settings.

Values are read from environment variables and/or a local ``.env`` file.
See ``.env.example`` for the full list of supported keys.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the Nexa Commerce API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application metadata -------------------------------------------------
    PROJECT_NAME: str = "Nexa Commerce API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "Production-grade REST API for Nexa - a modern e-commerce platform. "
        "Provides authentication, catalog browsing with faceted search, cart and "
        "coupon handling, wishlists, order management and an admin analytics suite."
    )
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    # --- Security -------------------------------------------------------------
    SECRET_KEY: str = "nexa-super-secret-change-me-in-production-0f4c1a9b7e2d"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # one week
    PBKDF2_ITERATIONS: int = 260_000

    # --- Database -------------------------------------------------------------
    DATABASE_URL: str = "sqlite:///./nexa.db"
    SQL_ECHO: bool = False

    # --- CORS -----------------------------------------------------------------
    # Stored as a comma separated string so plain ``.env`` files stay simple
    # (pydantic-settings would otherwise expect JSON for a list field).
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Seeding --------------------------------------------------------------
    AUTO_SEED: bool = True
    ADMIN_EMAIL: str = "admin@nexa.com"
    ADMIN_PASSWORD: str = "Admin@123"
    ADMIN_NAME: str = "Aarav Mehta"
    DEMO_EMAIL: str = "demo@nexa.com"
    DEMO_PASSWORD: str = "Demo@123"
    DEMO_NAME: str = "Priya Sharma"

    # --- Commerce rules (single source of truth for pricing) ------------------
    FREE_SHIPPING_THRESHOLD: float = 999.0
    SHIPPING_FLAT_RATE: float = 49.0
    TAX_RATE: float = 0.05  # 5% GST
    CURRENCY: str = "INR"
    DEFAULT_PAGE_SIZE: int = 12
    MAX_PAGE_SIZE: int = 100

    @property
    def cors_origins_list(self) -> List[str]:
        """CORS origins as a clean list of strings."""
        raw = (self.CORS_ORIGINS or "").strip()
        if not raw:
            return []
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings: Settings = get_settings()
