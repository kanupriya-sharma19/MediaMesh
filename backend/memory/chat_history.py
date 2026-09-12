"""PostgreSQL-backed persistent chat history."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from backend.database import Conversation, ConversationSummary, Message, session_scope
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy import delete, select

_store = object()


def get_store() -> object:
    return _store


def _now() -> datetime:
    return datetime.now(UTC)


def _title_from_messages(messages: Sequence[BaseMessage]) -> str:
    first_user_message = next(
        (message.content for message in messages if isinstance(message, HumanMessage)),
        "",
    )
    text = " ".join(str(first_user_message).split())
    if text.lower().startswith("can you "):
        text = text[8:]
    if len(text) <= 42:
        return text or "New conversation"
    truncated = text[:42].rsplit(" ", 1)[0].rstrip(".,!?;:")
    return f"{truncated}..."


def _serialize_message(message: BaseMessage) -> dict[str, str]:
    if isinstance(message, HumanMessage):
        role = "user"
    elif isinstance(message, AIMessage):
        role = "assistant"
    else:
        raise TypeError(f"Unsupported chat message type: {type(message).__name__}")
    return {"role": role, "content": str(message.content)}


def _deserialize_message(message: Message) -> BaseMessage:
    return (
        HumanMessage(content=message.content)
        if message.role == "user"
        else AIMessage(content=message.content)
    )


def create_chat_session(user_id: str) -> dict[str, str]:
    session_id = str(uuid.uuid4())
    now = _now()
    with session_scope() as session:
        session.add(
            Conversation(
                id=session_id,
                user_id=user_id,
                title="New conversation",
                created_at=now,
                updated_at=now,
            )
        )
    return {
        "id": session_id,
        "title": "New conversation",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }


def get_chat_history(user_id: str, session_id: str = "default") -> list[BaseMessage]:
    with session_scope() as session:
        rows = session.scalars(
            select(Message)
            .where(Message.user_id == user_id, Message.conversation_id == session_id)
            .order_by(Message.id)
        ).all()
    return [_deserialize_message(row) for row in rows]


def get_chat_sessions(user_id: str) -> list[dict[str, str]]:
    with session_scope() as session:
        rows = session.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        ).all()
    return [
        {
            "id": row.id,
            "title": row.title,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
        }
        for row in rows
    ]


def get_conversation_summary(user_id: str, session_id: str) -> str | None:
    with session_scope() as session:
        row = session.scalar(
            select(ConversationSummary).where(
                ConversationSummary.user_id == user_id,
                ConversationSummary.conversation_id == session_id,
            )
        )
    return row.summary if row else None


def save_conversation_summary(user_id: str, session_id: str, summary: str) -> None:
    if not summary.strip():
        return
    now = _now()
    with session_scope() as session:
        conversation = session.scalar(
            select(Conversation).where(
                Conversation.user_id == user_id, Conversation.id == session_id
            )
        )
        if conversation is None:
            return
        existing = session.scalar(
            select(ConversationSummary).where(
                ConversationSummary.user_id == user_id,
                ConversationSummary.conversation_id == session_id,
            )
        )
        if existing:
            existing.summary = summary.strip()
            existing.updated_at = now
        else:
            session.add(
                ConversationSummary(
                    conversation_id=session_id,
                    user_id=user_id,
                    summary=summary.strip(),
                    updated_at=now,
                )
            )


def summarize_messages(messages: Sequence[BaseMessage], max_chars: int = 4000) -> str:
    lines = [
        f"{message.type}: {' '.join(str(message.content).split())}"
        for message in messages
        if isinstance(message, (HumanMessage, AIMessage))
    ]
    return "\n".join(lines)[:max_chars].rstrip()


def save_chat_history(
    user_id: str, messages: Sequence[BaseMessage], session_id: str = "default"
) -> None:
    serialized = [_serialize_message(message) for message in messages]
    now = _now()
    title = _title_from_messages(messages)
    with session_scope() as session:
        conversation = session.scalar(
            select(Conversation).where(
                Conversation.id == session_id, Conversation.user_id == user_id
            )
        )
        if conversation is None:
            session.add(
                Conversation(
                    id=session_id,
                    user_id=user_id,
                    title=title,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            if conversation.title == "New conversation":
                conversation.title = title
            conversation.updated_at = now
        session.query(Message).filter(
            Message.conversation_id == session_id, Message.user_id == user_id
        ).delete(synchronize_session=False)
        session.add_all(
            [
                Message(
                    conversation_id=session_id,
                    user_id=user_id,
                    role=item["role"],
                    content=item["content"],
                    created_at=now,
                )
                for item in serialized
            ]
        )


def clear_chat_history(user_id: str, session_id: str = "default") -> None:
    with session_scope() as session:
        session.execute(delete(Conversation).where(Conversation.user_id == user_id))
