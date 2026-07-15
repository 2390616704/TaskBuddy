from pathlib import Path

import pytest

from app.domain.messages import MessageStatus
from app.repositories.conversations import ConversationRepository
from app.repositories.database import Database


@pytest.fixture
async def repository(tmp_path: Path) -> ConversationRepository:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'taskbuddy.db'}")
    await database.create_schema()
    async with database.session() as session:
        repository = ConversationRepository(session)
        await repository.create_conversation(
            conversation_id="c1",
            agent_id="work-assistant",
            title="测试会话",
        )
        yield repository
    await database.dispose()


async def test_client_message_id_is_idempotent(repository: ConversationRepository) -> None:
    first = await repository.create_exchange("c1", "client-1", "风险是什么")
    second = await repository.create_exchange("c1", "client-1", "风险是什么")

    assert second.user.id == first.user.id
    assert second.assistant.id == first.assistant.id


async def test_terminal_status_cannot_be_overwritten(
    repository: ConversationRepository,
) -> None:
    exchange = await repository.create_exchange("c1", "client-2", "分析风险")

    assert await repository.transition(
        exchange.assistant.id,
        MessageStatus.PENDING,
        MessageStatus.STREAMING,
    )
    assert await repository.transition(
        exchange.assistant.id,
        MessageStatus.STREAMING,
        MessageStatus.CANCELLED,
    )
    assert not await repository.transition(
        exchange.assistant.id,
        MessageStatus.STREAMING,
        MessageStatus.COMPLETED,
    )


async def test_messages_survive_database_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "persistent.db"
    database = Database(f"sqlite+aiosqlite:///{database_path}")
    await database.create_schema()
    async with database.session() as session:
        repository = ConversationRepository(session)
        await repository.create_conversation("c1", "work-assistant", "持久化会话")
        created = await repository.create_exchange("c1", "client-3", "保留这条消息")
    await database.dispose()

    reopened = Database(f"sqlite+aiosqlite:///{database_path}")
    async with reopened.session() as session:
        messages = await ConversationRepository(session).list_messages("c1")
    await reopened.dispose()

    assert [message.id for message in messages] == [created.user.id, created.assistant.id]
    assert messages[0].content == "保留这条消息"
