import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.application.runs import RunRegistry
from app.domain.provider import ModelEvent, ModelRequest
from app.main import create_app

from .test_streaming import create_conversation, parse_events


class BlockingProvider:
    name = "blocking"

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        yield ModelEvent.delta_event(1, '{"mode":"answer"')
        await request.cancel.wait()
        yield ModelEvent.cancelled()


def test_registry_allows_only_one_active_run_per_conversation() -> None:
    registry = RunRegistry()

    first = registry.reserve("c1")
    second = registry.reserve("c1")

    assert first is not None
    assert second is None
    registry.release("c1", first)
    assert registry.reserve("c1") is not None


async def test_cancel_endpoint_stops_stream_and_persists_cancelled(tmp_path: Path) -> None:
    app: FastAPI = create_app(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'cancel.db'}",
        provider=BlockingProvider(),
    )
    await app.state.database.create_schema()
    transport = ASGITransport(app=app)

    async with (
        AsyncClient(transport=transport, base_url="http://test") as stream_client,
        AsyncClient(transport=transport, base_url="http://test") as control_client,
    ):
        conversation_id = await create_conversation(control_client)
        stream_task = asyncio.create_task(
            stream_client.post(
                f"/api/conversations/{conversation_id}/messages",
                json={
                    "content": "等待取消",
                    "agentId": "work-assistant",
                    "clientMessageId": "client-cancel",
                },
            )
        )

        for _ in range(100):
            history = await control_client.get(f"/api/conversations/{conversation_id}/messages")
            if history.json() and history.json()[-1]["status"] == "streaming":
                break
            await asyncio.sleep(0.01)
        assistant_id = history.json()[-1]["id"]

        cancelled = await control_client.post(
            f"/api/conversations/{conversation_id}/messages/{assistant_id}/cancel"
        )
        streamed = await asyncio.wait_for(stream_task, timeout=2)

        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"
        assert parse_events(streamed.text)[-1][0] == "message.cancelled"
        refreshed = await control_client.get(f"/api/conversations/{conversation_id}/messages")
        assert refreshed.json()[-1]["status"] == "cancelled"

    await app.state.database.dispose()
