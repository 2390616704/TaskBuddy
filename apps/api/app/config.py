from typing import Literal, Self

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    model_provider: Literal["mock", "deepseek"] = "mock"
    database_url: str = "sqlite+aiosqlite:///./data/taskbuddy.db"
    deepseek_code_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("DEEPSEEK_CODE_API_KEY", "DEEPSEEK_API_KEY"),
    )
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"

    @model_validator(mode="after")
    def require_deepseek_key(self) -> Self:
        if self.model_provider == "deepseek" and self.deepseek_code_api_key is None:
            raise ValueError("DEEPSEEK_CODE_API_KEY is required when MODEL_PROVIDER=deepseek")
        return self
