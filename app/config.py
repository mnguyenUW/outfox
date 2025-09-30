"""Application configuration."""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore"
    )
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/healthcare_db"
    database_echo: bool = False
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4"
    
    # App Settings
    app_name: str = "Healthcare Cost Navigator"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Geographic Settings
    default_search_radius_km: float = 50.0
    max_search_radius_km: float = 500.0
    
    # API Settings
    api_prefix: str = ""
    cors_origins: list[str] = ["*"]
    
    @property
    def sync_database_url(self) -> str:
        """Get synchronous database URL for migrations."""
        return self.database_url.replace("+asyncpg", "")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()