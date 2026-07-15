from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.conversations import router as conversations_router
from app.application.runs import RunRegistry
from app.domain.provider import ModelProvider
from app.providers.mock import MockModelProvider
from app.repositories.database import Database


def create_app(
    database_url: str = "sqlite+aiosqlite:///./data/taskbuddy.db",
    provider: ModelProvider | None = None,
) -> FastAPI:
    database = Database(database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await database.create_schema()
        yield
        await database.dispose()

    application = FastAPI(title="TaskBuddy API", lifespan=lifespan)
    application.state.database = database
    application.state.provider = provider or MockModelProvider()
    application.state.run_registry = RunRegistry()
    application.include_router(conversations_router)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
