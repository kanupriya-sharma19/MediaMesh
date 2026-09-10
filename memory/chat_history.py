"""Simple process-local chat history backed by InMemoryStore."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.store.memory import InMemoryStore


logger = logging.getLogger(__name__)
_store = InMemoryStore()
_HISTORY_KEY = "messages"


def get_store() -> InMemoryStore:
    """Return the single store shared for this application process."""
    return _store


def _namespace(user_id: str) -> tuple[str, str]:
    return ("chat_history", user_id)


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


def get_chat_history(user_id: str) -> list[BaseMessage]:
    """Load a user's history, returning an empty list if storage fails."""
    try:
        item = get_store().get(_namespace(user_id), _HISTORY_KEY)
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


def save_chat_history(user_id: str, messages: Sequence[BaseMessage]) -> None:
    """Save a user's ordered chat messages without propagating storage errors."""
    try:
        serialized = [_serialize_message(message) for message in messages]
        get_store().put(_namespace(user_id), _HISTORY_KEY, {_HISTORY_KEY: serialized})
    except Exception:
        logger.exception("Could not save chat history for user %s", user_id)


def clear_chat_history(user_id: str) -> None:
    """Delete only the requested user's chat history."""
    try:
        get_store().delete(_namespace(user_id), _HISTORY_KEY)
    except Exception:
        logger.exception("Could not clear chat history for user %s", user_id)
