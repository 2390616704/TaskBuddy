import json

from httpx import AsyncClient


def parse_events(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in body.strip().split("\n\n"):
        lines = block.splitlines()
        name = next(line.removeprefix("event: ") for line in lines if line.startswith("event: "))
        data = next(line.removeprefix("data: ") for line in lines if line.startswith("data: "))
        events.append((name, json.loads(data)))
    return events


async def create_conversation(client: AsyncClient) -> str:
    response = await client.post("/api/conversations", json={"agentId": "work-assistant"})
    return response.json()["id"]


async def test_stream_emits_named_events_and_persists_completion(client: AsyncClient) -> None:
    conversation_id = await create_conversation(client)

    response = await client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={
            "content": "帮我梳理本周发布风险",
            "agentId": "work-assistant",
            "clientMessageId": "client-1",
        },
    )
    events = parse_events(response.text)

    assert response.status_code == 200
    assert events[0][0] == "message.accepted"
    assert any(name == "message.delta" for name, _ in events)
    assert events[-1][0] == "message.completed"

    history = await client.get(f"/api/conversations/{conversation_id}/messages")
    assistant = history.json()[-1]
    assert assistant["status"] == "completed"
    assert assistant["content"]["mode"] == "answer"


async def test_provider_failure_is_persisted_and_streamed(client: AsyncClient) -> None:
    conversation_id = await create_conversation(client)

    response = await client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={
            "content": "[mock:error]",
            "agentId": "work-assistant",
            "clientMessageId": "client-error",
        },
    )
    events = parse_events(response.text)

    assert events[-1][0] == "message.error"
    assert events[-1][1]["code"] == "MODEL_UNAVAILABLE"
    assert events[-1][1]["requestId"]

    history = await client.get(f"/api/conversations/{conversation_id}/messages")
    assert history.json()[-1]["status"] == "failed"
    assert history.json()[-1]["errorCode"] == "MODEL_UNAVAILABLE"


async def test_retry_creates_a_new_assistant_attempt_without_copying_user(
    client: AsyncClient,
) -> None:
    conversation_id = await create_conversation(client)
    first = await client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={
            "content": "[mock:error]",
            "agentId": "work-assistant",
            "clientMessageId": "client-retry",
        },
    )
    failed_id = parse_events(first.text)[0][1]["messageId"]

    retried = await client.post(f"/api/conversations/{conversation_id}/messages/{failed_id}/retry")
    assert retried.status_code == 200
    events = parse_events(retried.text)
    history = (await client.get(f"/api/conversations/{conversation_id}/messages")).json()

    assert events[0][0] == "message.accepted"
    assert len([message for message in history if message["role"] == "user"]) == 1
    assert len([message for message in history if message["role"] == "assistant"]) == 2
    assert history[-1]["retryOfMessageId"] == failed_id
