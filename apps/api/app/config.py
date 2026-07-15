from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    model_provider: Literal["mock", "openai-compatible"] = "mock"
    database_url: str = "sqlite+aiosqlite:///./data/taskbuddy.db"
    model_api_key: SecretStr | None = None
    model_base_url: str = "https://api.deepseek.com"
    model_name: str = "deepseek-v4-flash"
    model_display_name: str = "DeepSeek"
