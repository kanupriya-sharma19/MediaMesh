"""Simple process-local chat history backed by InMemoryStore."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.store.memory import InMemoryStore


logger = logging.getLogger(__name__)
_store = InMemoryStore()
_HISTORY_KEY = "messages"
_SESSIONS_KEY = "sessions"


def get_store() -> InMemoryStore:
    """Return the single store shared for this application process."""
    return _store


def _namespace(user_id: str, session_id: str = "default") -> tuple[str, str, str]:
    return ("chat_history", user_id, session_id)


def _user_namespace(user_id: str) -> tuple[str, str]:
    return ("chat_history", user_id)


def _register_session(user_id: str, session_id: str) -> None:
    item = get_store().get(_user_namespace(user_id), _SESSIONS_KEY)
    stored_sessions = item.value.get(_SESSIONS_KEY, []) if item is not None else []
    now = datetime.now(timezone.utc).isoformat()
    sessions = _normalize_sessions(stored_sessions, now)
    existing = next(
        (session for session in sessions if session["id"] == session_id), None
    )
    if existing is None:
        history = get_chat_history(user_id, session_id)
        title = _title_from_messages(history)
        sessions.append(
            {
                "id": session_id,
                "title": title,
                "created_at": now,
                "updated_at": now,
            }
        )
    else:
        existing["updated_at"] = now
        if existing["title"] == "New conversation":
            existing["title"] = _title_from_messages(
                get_chat_history(user_id, session_id)
            )
    get_store().put(_user_namespace(user_id), _SESSIONS_KEY, {_SESSIONS_KEY: sessions})


def _normalize_sessions(stored_sessions: Any, now: str) -> list[dict[str, str]]:
    """Convert the original session-ID registry to metadata records."""
    if not isinstance(stored_sessions, list):
        return []
    normalized: list[dict[str, str]] = []
    for session in stored_sessions:
        if isinstance(session, str):
            normalized.append(
                {
                    "id": session,
                    "title": "New conversation",
                    "created_at": now,
                    "updated_at": now,
                }
            )
        elif isinstance(session, dict) and isinstance(session.get("id"), str):
            normalized.append(
                {
                    "id": session["id"],
                    "title": str(session.get("title") or "New conversation"),
                    "created_at": str(session.get("created_at") or now),
                    "updated_at": str(session.get("updated_at") or now),
                }
            )
    return normalized


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


def _deserialize_message(message: Any) -> BaseMessage | None:
    if not isinstance(message, dict):
        return None
    role = message.get("role")
    content = message.get("content")
    if not isinstance(content, str):
        return None
    if role == "user":
        return HumanMessage(content=content)
    if role == "assistant":
        return AIMessage(content=content)
    return None


def get_chat_history(user_id: str, session_id: str = "default") -> list[BaseMessage]:
    """Load a user's history, returning an empty list if storage fails."""
    try:
        item = get_store().get(_namespace(user_id, session_id), _HISTORY_KEY)
        value = item.value if item is not None else {}
        messages = value.get(_HISTORY_KEY, []) if isinstance(value, dict) else []
        return [
            deserialized
            for message in messages
            if (deserialized := _deserialize_message(message)) is not None
        ]
    except Exception:
        logger.exception("Could not retrieve chat history for user %s", user_id)
        return []


def get_chat_sessions(user_id: str) -> list[dict[str, str]]:
    """Return the user's conversations, newest activity first."""
    try:
        item = get_store().get(_user_namespace(user_id), _SESSIONS_KEY)
        stored_sessions = item.value.get(_SESSIONS_KEY, []) if item is not None else []
        sessions = _normalize_sessions(
            stored_sessions, datetime.now(timezone.utc).isoformat()
        )
        return sorted(sessions, key=lambda session: session["updated_at"], reverse=True)
    except Exception:
        logger.exception("Could not retrieve sessions for user %s", user_id)
        return []


def save_chat_history(
    user_id: str, messages: Sequence[BaseMessage], session_id: str = "default"
) -> None:
    """Save a user's ordered chat messages without propagating storage errors."""
    try:
        serialized = [_serialize_message(message) for message in messages]
        get_store().put(
            _namespace(user_id, session_id), _HISTORY_KEY, {_HISTORY_KEY: serialized}
        )
        _register_session(user_id, session_id)
    except Exception:
        logger.exception("Could not save chat history for user %s", user_id)


def clear_chat_history(user_id: str, session_id: str = "default") -> None:
    """Delete all of a user's sessions, messages, and session metadata."""
    item = get_store().get(_user_namespace(user_id), _SESSIONS_KEY)
    stored_sessions = item.value.get(_SESSIONS_KEY, []) if item is not None else []
    sessions = _normalize_sessions(stored_sessions, "")
    for stored_session in sessions:
        get_store().delete(_namespace(user_id, stored_session["id"]), _HISTORY_KEY)
    get_store().delete(_namespace(user_id, session_id), _HISTORY_KEY)
    get_store().delete(_user_namespace(user_id), _SESSIONS_KEY)
