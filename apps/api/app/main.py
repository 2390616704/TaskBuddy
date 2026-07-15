from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.conversations import router as conversations_router
from app.application.runs import RunRegistry
from app.config import Settings
from app.domain.provider import ModelProvider
from app.providers.factory import build_provider
from app.repositories.database import Database


def create_app(
    database_url: str | None = None,
    provider: ModelProvider | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings()
    database = Database(database_url or resolved_settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await database.create_schema()
        yield
        await database.dispose()

    application = FastAPI(title="TaskBuddy API", lifespan=lifespan)
    application.state.database = database
    application.state.provider = provider or build_provider(resolved_settings)
    application.state.run_registry = RunRegistry()
    application.include_router(conversations_router)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
