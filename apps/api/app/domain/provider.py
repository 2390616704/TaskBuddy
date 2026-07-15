import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

from app.prompt.models import PromptPackage


class CancelSignal:
    def __init__(self) -> None:
        self._event = asyncio.Event()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()

    async def wait(self) -> None:
        await self._event.wait()


@dataclass(frozen=True, slots=True)
class ModelRequest:
    prompt: PromptPackage
    cancel: CancelSignal


@dataclass(frozen=True, slots=True)
class ModelEvent:
    type: Literal["delta", "completed", "cancelled", "error"]
    sequence: int | None = None
    delta: str | None = None
    code: str | None = None
    message: str | None = None
    retryable: bool = False

    @classmethod
    def delta_event(cls, sequence: int, delta: str) -> "ModelEvent":
        return cls(type="delta", sequence=sequence, delta=delta)

    @classmethod
    def completed(cls) -> "ModelEvent":
        return cls(type="completed")

    @classmethod
    def cancelled(cls) -> "ModelEvent":
        return cls(type="cancelled")

    @classmethod
    def error(cls, code: str, message: str, retryable: bool) -> "ModelEvent":
        return cls(type="error", code=code, message=message, retryable=retryable)


class ModelProvider(Protocol):
    name: str

    def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]: ...
