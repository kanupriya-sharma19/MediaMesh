"""SQLite-backed persistent chat history."""

from __future__ import annotations

import os
import sqlite3
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


_DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "mm.db"
_database_path = Path(os.getenv("MEDIAMESH_DB_PATH", str(_DEFAULT_DATABASE_PATH)))
_database_path.parent.mkdir(parents=True, exist_ok=True)
_store = object()


def get_store() -> object:
    """Retain the old accessor for callers that only need a store identity."""
    return _store


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _initialize() -> None:
    with _connect() as connection:
        existing = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'conversations'"
        ).fetchone()
        if existing and "PRIMARY KEY (user_id, id)" not in (existing["sql"] or ""):
            connection.execute("ALTER TABLE messages RENAME TO messages_legacy")
            connection.execute(
                "ALTER TABLE conversations RENAME TO conversations_legacy"
            )
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, id)
            );
            CREATE INDEX IF NOT EXISTS conversations_user_updated_idx
                ON conversations(user_id, updated_at DESC);
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id, conversation_id)
                    REFERENCES conversations(user_id, id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS messages_conversation_idx
                ON messages(conversation_id, id);
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                conversation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                summary TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, conversation_id),
                FOREIGN KEY (user_id, conversation_id)
                    REFERENCES conversations(user_id, id) ON DELETE CASCADE
            );
            """
        )
        if existing and "PRIMARY KEY (user_id, id)" not in (existing["sql"] or ""):
            connection.execute(
                """
                INSERT INTO conversations (id, user_id, title, created_at, updated_at)
                SELECT id, user_id, title, created_at, updated_at
                FROM conversations_legacy
                """
            )
            connection.execute(
                """
                INSERT INTO messages (conversation_id, user_id, role, content, created_at)
                SELECT messages_legacy.conversation_id, conversations_legacy.user_id,
                       messages_legacy.role, messages_legacy.content, messages_legacy.created_at
                FROM messages_legacy
                JOIN conversations_legacy
                  ON conversations_legacy.id = messages_legacy.conversation_id
                """
            )
            connection.execute("DROP TABLE messages_legacy")
            connection.execute("DROP TABLE conversations_legacy")


_initialize()


def _now() -> str:
    return datetime.now(UTC).isoformat()


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


def _deserialize_message(message: sqlite3.Row) -> BaseMessage:
    if message["role"] == "user":
        return HumanMessage(content=message["content"])
    return AIMessage(content=message["content"])


def create_chat_session(user_id: str) -> dict[str, str]:
    """Create an empty conversation owned by the authenticated user."""
    session_id = str(uuid.uuid4())
    now = _now()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO conversations (id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, user_id, "New conversation", now, now),
        )
    return {
        "id": session_id,
        "title": "New conversation",
        "created_at": now,
        "updated_at": now,
    }


def get_chat_history(user_id: str, session_id: str = "default") -> list[BaseMessage]:
    """Load messages only when the conversation belongs to the user."""
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT messages.role, messages.content
            FROM messages
            JOIN conversations ON conversations.id = messages.conversation_id
                AND conversations.user_id = messages.user_id
            WHERE messages.conversation_id = ? AND messages.user_id = ?
            ORDER BY messages.id
            """,
            (session_id, user_id),
        ).fetchall()
    return [_deserialize_message(row) for row in rows]


def get_chat_sessions(user_id: str) -> list[dict[str, str]]:
    """Return the user's conversations, newest activity first."""
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_conversation_summary(user_id: str, session_id: str) -> str | None:
    """Return the summary only when the conversation belongs to the user."""
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT summary
            FROM conversation_summaries
            WHERE user_id = ? AND conversation_id = ?
            """,
            (user_id, session_id),
        ).fetchone()
    return row["summary"] if row else None


def save_conversation_summary(user_id: str, session_id: str, summary: str) -> None:
    """Upsert a bounded summary for an owned conversation."""
    if not summary.strip():
        return
    now = _now()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO conversation_summaries
                (conversation_id, user_id, summary, updated_at)
            SELECT ?, ?, ?, ?
            WHERE EXISTS (
                SELECT 1 FROM conversations WHERE id = ? AND user_id = ?
            )
            ON CONFLICT(user_id, conversation_id) DO UPDATE SET
                summary = excluded.summary,
                updated_at = excluded.updated_at
            """,
            (session_id, user_id, summary.strip(), now, session_id, user_id),
        )


def summarize_messages(messages: Sequence[BaseMessage], max_chars: int = 4000) -> str:
    """Create a deterministic fallback summary without another model request."""
    lines = [
        f"{message.type}: {' '.join(str(message.content).split())}"
        for message in messages
        if isinstance(message, (HumanMessage, AIMessage))
    ]
    return "\n".join(lines)[:max_chars].rstrip()


def save_chat_history(
    user_id: str, messages: Sequence[BaseMessage], session_id: str = "default"
) -> None:
    """Persist the ordered messages and update conversation metadata."""
    serialized = [_serialize_message(message) for message in messages]
    now = _now()
    title = _title_from_messages(messages)
    with _connect() as connection:
        conversation = connection.execute(
            "SELECT title FROM conversations WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
        if conversation is None:
            connection.execute(
                """
                INSERT INTO conversations (id, user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, user_id, title, now, now),
            )
        else:
            next_title = (
                title
                if conversation["title"] == "New conversation"
                else conversation["title"]
            )
            connection.execute(
                """
                UPDATE conversations
                SET title = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
                """,
                (next_title, now, session_id, user_id),
            )
        connection.execute(
            "DELETE FROM messages WHERE conversation_id = ? AND user_id = ?",
            (session_id, user_id),
        )
        connection.executemany(
            """
            INSERT INTO messages (conversation_id, user_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (session_id, user_id, item["role"], item["content"], now)
                for item in serialized
            ],
        )


def clear_chat_history(user_id: str, session_id: str = "default") -> None:
    """Delete every conversation owned by the user."""
    with _connect() as connection:
        connection.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
