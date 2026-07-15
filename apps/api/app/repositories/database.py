from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.repositories.models import Base


class Database:
    def __init__(self, url: str) -> None:
        parsed = make_url(url)
        if (
            parsed.drivername.startswith("sqlite")
            and parsed.database
            and parsed.database != ":memory:"
        ):
            Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_async_engine(url)
        self._sessions = async_sessionmaker(self._engine, expire_on_commit=False)

    async def create_schema(self) -> None:
        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            if self._engine.dialect.name == "sqlite":
                columns = await connection.execute(text("PRAGMA table_info(conversations)"))
                if "provider_id" not in {str(row[1]) for row in columns}:
                    await connection.execute(
                        text(
                            "ALTER TABLE conversations ADD COLUMN provider_id "
                            "VARCHAR(80) NOT NULL DEFAULT 'mock'"
                        )
                    )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._sessions() as session:
            yield session

    async def dispose(self) -> None:
        await self._engine.dispose()
