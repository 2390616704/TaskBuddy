from typing import Literal

from pydantic import BaseModel


class PromptMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class PromptPackage(BaseModel):
    messages: list[PromptMessage]
    prompt_version: str
    output_schema: dict[str, object]
