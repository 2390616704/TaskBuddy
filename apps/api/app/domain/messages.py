from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageStatus(StrEnum):
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


TERMINAL_STATUSES = frozenset(
    {MessageStatus.COMPLETED, MessageStatus.CANCELLED, MessageStatus.FAILED}
)


@dataclass(frozen=True, slots=True)
class Message:
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    status: MessageStatus
    in_reply_to_message_id: str | None
    retry_of_message_id: str | None
    error_code: str | None
    client_message_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Exchange:
    user: Message
    assistant: Message
