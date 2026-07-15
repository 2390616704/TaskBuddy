from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.messages import Conversation, Exchange, Message, MessageRole, MessageStatus
from app.repositories.models import ConversationRow, MessageRow


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_conversation(
        self,
        conversation_id: str,
        agent_id: str,
        title: str,
    ) -> Conversation:
        row = ConversationRow(id=conversation_id, agent_id=agent_id, title=title)
        self._session.add(row)
        await self._session.commit()
        return self._to_conversation(row)

    async def list_conversations(self) -> list[Conversation]:
        rows = (
            await self._session.scalars(
                select(ConversationRow).order_by(ConversationRow.updated_at.desc())
            )
        ).all()
        return [self._to_conversation(row) for row in rows]

    async def conversation_exists(self, conversation_id: str) -> bool:
        conversation = await self._session.scalar(
            select(ConversationRow.id).where(ConversationRow.id == conversation_id)
        )
        return conversation is not None

    async def create_exchange(
        self,
        conversation_id: str,
        client_message_id: str,
        content: str,
    ) -> Exchange:
        existing_user = await self._session.scalar(
            select(MessageRow).where(
                MessageRow.conversation_id == conversation_id,
                MessageRow.client_message_id == client_message_id,
            )
        )
        if existing_user is not None:
            existing_assistant = await self._session.scalar(
                select(MessageRow).where(
                    MessageRow.in_reply_to_message_id == existing_user.id,
                    MessageRow.retry_of_message_id.is_(None),
                )
            )
            if existing_assistant is None:
                raise RuntimeError("Idempotent exchange is missing its assistant message")
            return Exchange(self._to_message(existing_user), self._to_message(existing_assistant))

        now = datetime.now(UTC)
        user = MessageRow(
            id=str(uuid4()),
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=content,
            status=MessageStatus.COMPLETED,
            client_message_id=client_message_id,
            created_at=now,
            updated_at=now,
        )
        assistant_time = now + timedelta(microseconds=1)
        assistant = MessageRow(
            id=str(uuid4()),
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content="",
            status=MessageStatus.PENDING,
            in_reply_to_message_id=user.id,
            created_at=assistant_time,
            updated_at=assistant_time,
        )
        self._session.add_all([user, assistant])
        await self._session.commit()
        return Exchange(self._to_message(user), self._to_message(assistant))

    async def transition(
        self,
        message_id: str,
        expected: MessageStatus,
        target: MessageStatus,
    ) -> bool:
        result = await self._session.execute(
            update(MessageRow)
            .where(MessageRow.id == message_id, MessageRow.status == expected)
            .values(status=target, updated_at=datetime.now(UTC))
            .returning(MessageRow.id)
        )
        changed_id = result.scalar_one_or_none()
        await self._session.commit()
        return changed_id is not None

    async def list_messages(self, conversation_id: str) -> list[Message]:
        query: Select[tuple[MessageRow]] = (
            select(MessageRow)
            .where(MessageRow.conversation_id == conversation_id)
            .order_by(MessageRow.created_at)
        )
        rows = (await self._session.scalars(query)).all()
        return [self._to_message(row) for row in rows]

    async def get_message(self, message_id: str) -> Message | None:
        row = await self._session.get(MessageRow, message_id)
        return self._to_message(row) if row is not None else None

    async def create_retry(self, assistant_message_id: str) -> Exchange | None:
        original = await self._session.get(MessageRow, assistant_message_id)
        if (
            original is None
            or original.role != MessageRole.ASSISTANT
            or original.status not in {MessageStatus.FAILED, MessageStatus.CANCELLED}
            or original.in_reply_to_message_id is None
        ):
            return None
        user = await self._session.get(MessageRow, original.in_reply_to_message_id)
        if user is None or user.role != MessageRole.USER:
            return None
        now = datetime.now(UTC)
        retry = MessageRow(
            id=str(uuid4()),
            conversation_id=original.conversation_id,
            role=MessageRole.ASSISTANT,
            content="",
            status=MessageStatus.PENDING,
            in_reply_to_message_id=user.id,
            retry_of_message_id=original.id,
            created_at=now,
            updated_at=now,
        )
        self._session.add(retry)
        await self._session.commit()
        return Exchange(self._to_message(user), self._to_message(retry))

    async def append_delta(self, message_id: str, delta: str) -> bool:
        row = await self._session.scalar(
            select(MessageRow).where(
                MessageRow.id == message_id,
                MessageRow.status == MessageStatus.STREAMING,
            )
        )
        if row is None:
            return False
        row.content += delta
        row.updated_at = datetime.now(UTC)
        await self._session.commit()
        return True

    async def complete(self, message_id: str, content: str) -> bool:
        result = await self._session.execute(
            update(MessageRow)
            .where(
                MessageRow.id == message_id,
                MessageRow.status == MessageStatus.STREAMING,
            )
            .values(
                status=MessageStatus.COMPLETED,
                content=content,
                updated_at=datetime.now(UTC),
            )
            .returning(MessageRow.id)
        )
        await self._session.commit()
        return result.scalar_one_or_none() is not None

    async def fail(self, message_id: str, error_code: str) -> bool:
        result = await self._session.execute(
            update(MessageRow)
            .where(
                MessageRow.id == message_id,
                MessageRow.status.in_([MessageStatus.PENDING, MessageStatus.STREAMING]),
            )
            .values(
                status=MessageStatus.FAILED,
                error_code=error_code,
                updated_at=datetime.now(UTC),
            )
            .returning(MessageRow.id)
        )
        await self._session.commit()
        return result.scalar_one_or_none() is not None

    @staticmethod
    def _to_conversation(row: ConversationRow) -> Conversation:
        return Conversation(
            id=row.id,
            agent_id=row.agent_id,
            title=row.title,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_message(row: MessageRow) -> Message:
        return Message(
            id=row.id,
            conversation_id=row.conversation_id,
            role=MessageRole(row.role),
            content=row.content,
            status=MessageStatus(row.status),
            in_reply_to_message_id=row.in_reply_to_message_id,
            retry_of_message_id=row.retry_of_message_id,
            error_code=row.error_code,
            client_message_id=row.client_message_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
