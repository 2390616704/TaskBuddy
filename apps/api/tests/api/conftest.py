from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.providers.mock import MockModelProvider


@pytest.fixture
async def app(tmp_path: Path) -> FastAPI:
    application = create_app(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'api.db'}",
        provider=MockModelProvider(),
    )
    await application.state.database.create_schema()
    yield application
    await application.state.database.dispose()


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
