import asyncio
from collections.abc import AsyncIterator, Callable
from typing import cast

from agents import Agent, OpenAIChatCompletionsModel, Runner, TResponseInputItem
from agents import set_tracing_disabled
from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent

from app.config import Settings
from app.domain.provider import ModelEvent, ModelRequest

StreamFactory = Callable[[str, list[dict[str, str]]], AsyncIterator[str]]


async def wait_for_cancel(request: ModelRequest) -> str:
    await request.cancel.wait()
    return "cancelled"


class OpenAICompatibleProvider:
    name = "openai-compatible"

    def __init__(self, settings: Settings, stream_factory: StreamFactory | None = None) -> None:
        if settings.model_api_key is None:
            raise ValueError("MODEL_API_KEY is not configured")
        self.model_name = settings.model_name
        self.client = AsyncOpenAI(
            api_key=settings.model_api_key.get_secret_value(),
            base_url=settings.model_base_url,
        )
        self._model = OpenAIChatCompletionsModel(
            model=self.model_name,
            openai_client=self.client,
        )
        self._stream_factory = stream_factory or self._stream_agents
        set_tracing_disabled(disabled=True)

    async def _stream_agents(
        self, system_instructions: str, messages: list[dict[str, str]]
    ) -> AsyncIterator[str]:
        agent: Agent[object] = Agent(
            name="工作事项助手",
            instructions=system_instructions,
            model=self._model,
        )
        result = Runner.run_streamed(
            agent,
            input=cast(list[TResponseInputItem], messages),
        )
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(
                event.data, ResponseTextDeltaEvent
            ):
                yield event.data.delta

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        system_instructions = request.prompt.messages[0].content
        messages = [
            {"role": message.role, "content": message.content}
            for message in request.prompt.messages[1:]
        ]
        try:
            sequence = 0
            iterator = self._stream_factory(system_instructions, messages).__aiter__()
            while True:
                next_delta = asyncio.ensure_future(anext(iterator))
                cancelled = asyncio.create_task(wait_for_cancel(request))
                completed, _ = await asyncio.wait(
                    {next_delta, cancelled}, return_when=asyncio.FIRST_COMPLETED
                )
                if cancelled in completed:
                    next_delta.cancel()
                    await asyncio.gather(next_delta, return_exceptions=True)
                    yield ModelEvent.cancelled()
                    return
                cancelled.cancel()
                await asyncio.gather(cancelled, return_exceptions=True)
                try:
                    delta = next_delta.result()
                except StopAsyncIteration:
                    break
                sequence += 1
                yield ModelEvent.delta_event(sequence, delta)
            yield ModelEvent.completed()
        except Exception:
            yield ModelEvent.error("MODEL_UNAVAILABLE", "模型服务暂时不可用。", retryable=True)
