"""
Application configuration using Pydantic Settings.
Loads configuration from environment variables via .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings singleton.
    All configuration is loaded from environment variables.
    """

    # Application metadata
    app_name: str = "NisargHunterAI"
    app_version: str = "1.0.0"

    # Environment
    debug: bool = False

    # Security
    secret_key: str

    # Database
    database_url: str

    # Redis
    redis_url: str

    # External APIs
    anthropic_api_key: str = ""
    hackerone_username: str = ""
    hackerone_api_token: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Singleton settings instance
settings = Settings()
