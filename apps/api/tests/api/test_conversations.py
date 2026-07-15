from httpx import AsyncClient


async def test_create_list_and_read_conversation_messages(client: AsyncClient) -> None:
    created = await client.post(
        "/api/conversations",
        json={"agentId": "work-assistant"},
    )

    assert created.status_code == 201
    conversation = created.json()
    listed = await client.get("/api/conversations")
    messages = await client.get(f"/api/conversations/{conversation['id']}/messages")

    assert listed.json()[0]["id"] == conversation["id"]
    assert messages.status_code == 200
    assert messages.json() == []


async def test_missing_conversation_uses_stable_error_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/conversations/missing/messages")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CONVERSATION_NOT_FOUND"
    assert response.json()["error"]["requestId"]


async def test_local_frontend_origin_is_allowed_by_cors(client: AsyncClient) -> None:
    response = await client.options(
        "/api/conversations",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
