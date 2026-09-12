"""Idempotently import the legacy MediaMesh SQLite database into PostgreSQL.

Run after `alembic upgrade head`. The SQLite file is read only and never deleted.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select, text

from backend.database import (
    AuthSession,
    Conversation,
    ConversationSummary,
    Message,
    User,
    UserMemory,
    session_scope,
)

load_dotenv()


def _timestamp(value: str | None) -> datetime:
    parsed = datetime.fromisoformat(value or datetime.now(UTC).isoformat())
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _rows(connection: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    if (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        is None
    ):
        return []
    return connection.execute(f"SELECT * FROM {table}").fetchall()


def main() -> None:
    source_path = Path(os.getenv("MEDIAMESH_DB_PATH", "backend/data/mm.db"))
    if not source_path.exists():
        raise FileNotFoundError(f"SQLite source database not found: {source_path}")
    with sqlite3.connect(source_path) as source:
        source.row_factory = sqlite3.Row
        with session_scope() as destination:
            for row in _rows(source, "users"):
                if destination.get(User, row["id"]) is None:
                    destination.add(
                        User(
                            id=row["id"],
                            name=row["name"],
                            email=row["email"],
                            password_hash=row["password_hash"],
                        )
                    )
            destination.flush()
            for row in _rows(source, "sessions"):
                if destination.get(
                    AuthSession, row["token_hash"]
                ) is None and destination.get(User, row["user_id"]):
                    destination.add(
                        AuthSession(
                            token_hash=row["token_hash"],
                            user_id=row["user_id"],
                            expires_at=_timestamp(row["expires_at"]),
                        )
                    )
            for row in _rows(source, "conversations"):
                key = (row["id"], row["user_id"])
                if destination.get(Conversation, key) is None and destination.get(
                    User, row["user_id"]
                ):
                    destination.add(
                        Conversation(
                            id=row["id"],
                            user_id=row["user_id"],
                            title=row["title"],
                            created_at=_timestamp(row["created_at"]),
                            updated_at=_timestamp(row["updated_at"]),
                        )
                    )
            destination.flush()
            for row in _rows(source, "messages"):
                if destination.get(Message, row["id"]) is None and destination.get(
                    Conversation, (row["conversation_id"], row["user_id"])
                ):
                    destination.add(
                        Message(
                            id=row["id"],
                            conversation_id=row["conversation_id"],
                            user_id=row["user_id"],
                            role=row["role"],
                            content=row["content"],
                            created_at=_timestamp(row["created_at"]),
                        )
                    )
            for row in _rows(source, "conversation_summaries"):
                existing = destination.scalar(
                    select(ConversationSummary).where(
                        ConversationSummary.user_id == row["user_id"],
                        ConversationSummary.conversation_id == row["conversation_id"],
                    )
                )
                if existing is None and destination.get(
                    Conversation, (row["conversation_id"], row["user_id"])
                ):
                    destination.add(
                        ConversationSummary(
                            conversation_id=row["conversation_id"],
                            user_id=row["user_id"],
                            summary=row["summary"],
                            updated_at=_timestamp(row["updated_at"]),
                        )
                    )
            for row in _rows(source, "user_memories"):
                if destination.get(UserMemory, row["id"]) is None and destination.get(
                    User, row["user_id"]
                ):
                    duplicate = destination.scalar(
                        select(UserMemory).where(
                            UserMemory.user_id == row["user_id"],
                            UserMemory.memory == row["memory"],
                        )
                    )
                    if duplicate is None:
                        destination.add(
                            UserMemory(
                                id=row["id"],
                                user_id=row["user_id"],
                                memory=row["memory"],
                                category=row["category"],
                                created_at=_timestamp(row["created_at"]),
                                updated_at=_timestamp(row["updated_at"]),
                            )
                        )
            destination.flush()
            destination.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('messages', 'id'), COALESCE((SELECT MAX(id) FROM messages), 1), true)"
                )
            )
            destination.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence('conversation_summaries', 'id'), COALESCE((SELECT MAX(id) FROM conversation_summaries), 1), true)"
                )
            )
    print(f"Imported legacy SQLite data from {source_path} into PostgreSQL.")


if __name__ == "__main__":
    main()
