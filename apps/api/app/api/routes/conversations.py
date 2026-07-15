import json
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.api.errors import error_response
from app.api.sse import encode_sse
from app.application.conversations import (
    ConversationNotFoundError,
    ConversationService,
    InvalidRetryError,
)
from app.application.runs import RunRegistry
from app.domain.messages import Conversation, Message, MessageRole, MessageStatus
from app.repositories.conversations import ConversationRepository

router = APIRouter(prefix="/api/conversations")


class CreateConversationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_id: str = Field(alias="agentId")


class SendMessageRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    content: str = Field(min_length=1)
    agent_id: str = Field(alias="agentId")
    client_message_id: str = Field(alias="clientMessageId", min_length=1)


def serialize_conversation(conversation: Conversation) -> dict[str, object]:
    return {
        "id": conversation.id,
        "agentId": conversation.agent_id,
        "title": conversation.title,
        "createdAt": conversation.created_at.isoformat(),
        "updatedAt": conversation.updated_at.isoformat(),
    }


def serialize_message(message: Message) -> dict[str, object]:
    content: object = message.content
    if message.role == MessageRole.ASSISTANT and message.status == MessageStatus.COMPLETED:
        content = json.loads(message.content)
    return {
        "id": message.id,
        "conversationId": message.conversation_id,
        "role": message.role.value,
        "content": content,
        "status": message.status.value,
        "inReplyToMessageId": message.in_reply_to_message_id,
        "retryOfMessageId": message.retry_of_message_id,
        "errorCode": message.error_code,
        "createdAt": message.created_at.isoformat(),
        "updatedAt": message.updated_at.isoformat(),
    }


@router.post("", status_code=201)
async def create_conversation(
    payload: CreateConversationRequest, request: Request
) -> dict[str, object]:
    async with request.app.state.database.session() as session:
        conversation = await ConversationRepository(session).create_conversation(
            str(uuid4()),
            payload.agent_id,
            "新会话",
        )
    return serialize_conversation(conversation)


@router.get("")
async def list_conversations(request: Request) -> list[dict[str, object]]:
    async with request.app.state.database.session() as session:
        conversations = await ConversationRepository(session).list_conversations()
    return [serialize_conversation(conversation) for conversation in conversations]


@router.get("/{conversation_id}/messages")
async def list_messages(conversation_id: str, request: Request):
    async with request.app.state.database.session() as session:
        repository = ConversationRepository(session)
        if not await repository.conversation_exists(conversation_id):
            return error_response(404, "CONVERSATION_NOT_FOUND", "会话不存在。")
        messages = await repository.list_messages(conversation_id)
    return [serialize_message(message) for message in messages]


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    payload: SendMessageRequest,
    request: Request,
) -> Response:
    request_id = str(uuid4())
    registry: RunRegistry = request.app.state.run_registry
    lease = registry.reserve(conversation_id)
    if lease is None:
        return error_response(409, "CONVERSATION_BUSY", "该会话正在生成回答。")

    async def stream() -> AsyncIterator[bytes]:
        try:
            async with request.app.state.database.session() as session:
                service = ConversationService(
                    ConversationRepository(session),
                    request.app.state.provider,
                )
                async for name, data in service.stream_message(
                    conversation_id,
                    payload.content,
                    payload.client_message_id,
                    request_id,
                    lease.cancel,
                ):
                    if name == "message.accepted":
                        lease.message_id = str(data["messageId"])
                    if await request.is_disconnected():
                        lease.cancel.cancel()
                    yield encode_sse(name, data)
        except ConversationNotFoundError:
            yield encode_sse(
                "message.error",
                {
                    "messageId": "",
                    "code": "CONVERSATION_NOT_FOUND",
                    "message": "会话不存在。",
                    "requestId": request_id,
                    "retryable": False,
                },
            )
        finally:
            registry.release(conversation_id, lease)

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/{conversation_id}/messages/{message_id}/cancel", response_model=None)
async def cancel_message(
    conversation_id: str,
    message_id: str,
    request: Request,
) -> dict[str, str] | JSONResponse:
    registry: RunRegistry = request.app.state.run_registry
    async with request.app.state.database.session() as session:
        repository = ConversationRepository(session)
        message = await repository.get_message(message_id)
        if message is None or message.conversation_id != conversation_id:
            return error_response(404, "MESSAGE_NOT_FOUND", "消息不存在。")
        if message.status == MessageStatus.CANCELLED:
            return {"messageId": message_id, "status": "cancelled"}
        if not registry.cancel(conversation_id, message_id):
            return error_response(409, "GENERATION_NOT_ACTIVE", "该消息当前没有活动生成。")
        await repository.transition(
            message_id,
            MessageStatus.STREAMING,
            MessageStatus.CANCELLED,
        )
    return {"messageId": message_id, "status": "cancelled"}


@router.post("/{conversation_id}/messages/{message_id}/retry")
async def retry_message(
    conversation_id: str,
    message_id: str,
    request: Request,
) -> Response:
    request_id = str(uuid4())
    registry: RunRegistry = request.app.state.run_registry
    lease = registry.reserve(conversation_id)
    if lease is None:
        return error_response(409, "CONVERSATION_BUSY", "该会话正在生成回答。")

    async def stream() -> AsyncIterator[bytes]:
        try:
            async with request.app.state.database.session() as session:
                service = ConversationService(
                    ConversationRepository(session),
                    request.app.state.provider,
                )
                async for name, data in service.stream_retry(
                    conversation_id,
                    message_id,
                    request_id,
                    lease.cancel,
                ):
                    if name == "message.accepted":
                        lease.message_id = str(data["messageId"])
                    if await request.is_disconnected():
                        lease.cancel.cancel()
                    yield encode_sse(name, data)
        except (ConversationNotFoundError, InvalidRetryError):
            yield encode_sse(
                "message.error",
                {
                    "messageId": message_id,
                    "code": "RETRY_NOT_ALLOWED",
                    "message": "该消息当前不可重试。",
                    "requestId": request_id,
                    "retryable": False,
                },
            )
        finally:
            registry.release(conversation_id, lease)

    return StreamingResponse(stream(), media_type="text/event-stream")
