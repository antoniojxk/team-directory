from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str = Field(min_length=32)
    access_token_minutes: int = Field(default=30, ge=1, le=120)
    db_pool_size: int = Field(default=2, ge=1, le=5)
    static_dir: Path = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    frontend_origins: list[str] = []
    demo_viewer_password: str | None = None
    demo_hr_password: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
