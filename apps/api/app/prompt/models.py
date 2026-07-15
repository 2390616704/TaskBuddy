from typing import Literal

from pydantic import BaseModel, Field


class WorkAssistantResponse(BaseModel):
    mode: Literal["answer", "clarification", "refusal"]
    conclusion: str = ""
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    notice: str = ""


class PromptMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class PromptPackage(BaseModel):
    messages: list[PromptMessage]
    prompt_version: str
    output_schema: dict[str, object]
