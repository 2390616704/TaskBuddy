from collections.abc import AsyncGenerator, AsyncIterator

from app.domain.messages import Exchange, MessageRole, MessageStatus
from app.domain.provider import CancelSignal, ModelProvider, ModelRequest
from app.prompt.builder import PromptBuilder
from app.prompt.models import PromptMessage
from app.repositories.conversations import ConversationRepository


class ConversationNotFoundError(LookupError):
    pass


class InvalidRetryError(ValueError):
    pass


class ConversationService:
    def __init__(
        self,
        repository: ConversationRepository,
        provider: ModelProvider,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._prompt_builder = prompt_builder or PromptBuilder()

    async def stream_message(
        self,
        conversation_id: str,
        content: str,
        client_message_id: str,
        request_id: str,
        cancel: CancelSignal,
    ) -> AsyncIterator[tuple[str, dict[str, object]]]:
        if not await self._repository.conversation_exists(conversation_id):
            raise ConversationNotFoundError(conversation_id)
        exchange = await self._repository.create_exchange(
            conversation_id,
            client_message_id,
            content,
        )
        stream = self._stream_exchange(exchange, content, request_id, cancel)
        try:
            async for event in stream:
                yield event
        finally:
            await stream.aclose()

    async def stream_retry(
        self,
        conversation_id: str,
        assistant_message_id: str,
        request_id: str,
        cancel: CancelSignal,
    ) -> AsyncIterator[tuple[str, dict[str, object]]]:
        if not await self._repository.conversation_exists(conversation_id):
            raise ConversationNotFoundError(conversation_id)
        exchange = await self._repository.create_retry(assistant_message_id)
        if exchange is None or exchange.assistant.conversation_id != conversation_id:
            raise InvalidRetryError(assistant_message_id)
        stream = self._stream_exchange(
            exchange,
            exchange.user.content,
            request_id,
            cancel,
        )
        try:
            async for event in stream:
                yield event
        finally:
            await stream.aclose()

    async def _stream_exchange(
        self,
        exchange: Exchange,
        content: str,
        request_id: str,
        cancel: CancelSignal,
    ) -> AsyncGenerator[tuple[str, dict[str, object]], None]:
        yield (
            "message.accepted",
            {
                "requestId": request_id,
                "userMessageId": exchange.user.id,
                "messageId": exchange.assistant.id,
            },
        )
        if exchange.assistant.status == MessageStatus.COMPLETED:
            yield (
                "message.completed",
                {
                    "messageId": exchange.assistant.id,
                    "status": "completed",
                    "content": exchange.assistant.content,
                },
            )
            return

        started = await self._repository.transition(
            exchange.assistant.id,
            MessageStatus.PENDING,
            MessageStatus.STREAMING,
        )
        if not started:
            yield self._error_event(
                exchange.assistant.id,
                "GENERATION_STATE_CONFLICT",
                "消息当前状态不允许开始生成。",
                request_id,
                True,
            )
            return

        messages = await self._repository.list_messages(exchange.assistant.conversation_id)
        excluded_ids = {exchange.user.id, exchange.assistant.id}
        if exchange.assistant.retry_of_message_id is not None:
            excluded_ids.add(exchange.assistant.retry_of_message_id)
        history = [
            PromptMessage(role=message.role.value, content=message.content)
            for message in messages
            if message.id not in excluded_ids
            and message.role in {MessageRole.USER, MessageRole.ASSISTANT}
        ]
        prompt = self._prompt_builder.build(history, content)
        output = ""

        try:
            async for event in self._provider.stream(ModelRequest(prompt=prompt, cancel=cancel)):
                if event.type == "delta" and event.delta is not None and event.sequence is not None:
                    if not await self._repository.append_delta(exchange.assistant.id, event.delta):
                        continue
                    output += event.delta
                    yield (
                        "message.delta",
                        {
                            "messageId": exchange.assistant.id,
                            "sequence": event.sequence,
                            "delta": event.delta,
                        },
                    )
                elif event.type == "completed":
                    await self._repository.complete(exchange.assistant.id, output)
                    yield (
                        "message.completed",
                        {
                            "messageId": exchange.assistant.id,
                            "status": "completed",
                            "content": output,
                        },
                    )
                    return
                elif event.type == "cancelled":
                    await self._repository.transition(
                        exchange.assistant.id,
                        MessageStatus.STREAMING,
                        MessageStatus.CANCELLED,
                    )
                    yield (
                        "message.cancelled",
                        {"messageId": exchange.assistant.id, "status": "cancelled"},
                    )
                    return
                elif event.type == "error":
                    code = event.code or "MODEL_UNAVAILABLE"
                    await self._repository.fail(exchange.assistant.id, code)
                    yield self._error_event(
                        exchange.assistant.id,
                        code,
                        event.message or "模型服务不可用。",
                        request_id,
                        event.retryable,
                    )
                    return
        finally:
            cancel.cancel()
            await self._repository.transition(
                exchange.assistant.id,
                MessageStatus.STREAMING,
                MessageStatus.CANCELLED,
            )

    @staticmethod
    def _error_event(
        message_id: str,
        code: str,
        message: str,
        request_id: str,
        retryable: bool,
    ) -> tuple[str, dict[str, object]]:
        return (
            "message.error",
            {
                "messageId": message_id,
                "code": code,
                "message": message,
                "requestId": request_id,
                "retryable": retryable,
            },
        )
