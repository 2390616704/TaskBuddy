from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    application.state.database = database
    application.state.provider = provider or build_provider(resolved_settings)
    application.state.run_registry = RunRegistry()
    application.include_router(conversations_router)

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
