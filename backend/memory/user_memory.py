"""SQLite-backed, user-scoped long-term preference memory."""

from __future__ import annotations

import re
import uuid
import logging

from backend.memory.chat_history import _connect, _now


logger = logging.getLogger(__name__)

_NAME_PATTERNS = (
    re.compile(
        r"\bmy\s+name\s+is\s+([A-Za-z][A-Za-z'-]{1,39}(?:\s+[A-Za-z][A-Za-z'-]{1,39}){0,2})\b[.!?]?\s*$",
        re.I,
    ),
    re.compile(
        r"\bI(?:\s+am|'m)\s+([A-Za-z][A-Za-z'-]{1,39}(?:\s+[A-Za-z][A-Za-z'-]{1,39}){0,2})\b[.!?]?\s*$",
        re.I,
    ),
)
_PREFERENCE_PATTERNS = (
    re.compile(
        r"\bI\s+(?:really\s+)?(?:like|love|enjoy|prefer)\s+(.+?)[.!?]?\s*$", re.I
    ),
    re.compile(r"\bmy\s+favorite\s+([^.!?]+?)\s+is\s+(.+?)[.!?]?\s*$", re.I),
    re.compile(r"\bI\s+(?:don't|do not|dislike|hate)\s+(.+?)[.!?]?\s*$", re.I),
)


def _initialize() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_memories (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                memory TEXT NOT NULL,
                category TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, memory)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS user_memories_user_updated_idx
            ON user_memories(user_id, updated_at DESC)
            """
        )


_initialize()


def extract_memory(message: str) -> tuple[str, str] | None:
    """Extract only explicit, stable identity or preference statements."""
    normalized = " ".join(message.split())
    for pattern in _NAME_PATTERNS:
        match = pattern.search(normalized)
        if match:
            name = match.group(1).strip()
            if name.lower().split()[0] not in {"a", "an", "the", "looking"}:
                result = (f"User's name is {name}", "personal_information")
                logger.info("[MEMORY EXTRACTION] category=%s memory=%s", *result)
                return result
    for index, pattern in enumerate(_PREFERENCE_PATTERNS):
        match = pattern.search(normalized)
        if not match:
            continue
        if index == 1:
            memory = (
                f"User's favorite {match.group(1).strip()} is {match.group(2).strip()}"
            )
        elif index == 2:
            memory = f"User dislikes {match.group(1).strip()}"
        else:
            memory = f"User likes {match.group(1).strip()}"
        result = (memory[:500], "preference")
        logger.info("[MEMORY EXTRACTION] category=%s memory=%s", *result)
        return result
    logger.info("[MEMORY EXTRACTION] no stable memory found")
    return None


def save_memory(user_id: str, memory: str, category: str = "preference") -> None:
    """Persist or refresh one memory for the authenticated user."""
    now = _now()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO user_memories (id, user_id, memory, category, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, memory) DO UPDATE SET
                updated_at = excluded.updated_at,
                category = excluded.category
            """,
            (str(uuid.uuid4()), user_id, memory.strip(), category, now, now),
        )
    logger.info(
        "[MEMORY SAVED] user_id=%s category=%s memory=%s", user_id, category, memory
    )


def get_user_memories(user_id: str, limit: int = 12) -> list[dict[str, str]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, user_id, memory, category, created_at, updated_at
            FROM user_memories
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_relevant_memories(
    user_id: str, query: str, limit: int = 8
) -> list[dict[str, str]]:
    """Prefer memories matching the query, with preferences for recommendation asks."""
    memories = get_user_memories(user_id, limit=100)
    terms = {
        term.lower() for term in re.findall(r"[a-zA-Z0-9]+", query) if len(term) > 2
    }
    scored = []
    recommendation = re.search(
        r"\b(recommend|suggest|like|similar|favorite)\b", query, re.I
    )
    for position, memory in enumerate(memories):
        memory_terms = set(re.findall(r"[a-zA-Z0-9]+", memory["memory"].lower()))
        score = len(terms & memory_terms)
        if recommendation and memory["category"] == "preference":
            score += 1
        scored.append((score, -position, memory))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    relevant = [memory for score, _, memory in scored if score > 0][:limit]
    logger.info(
        "[MEMORY RETRIEVED] user_id=%s query=%r memories=%s",
        user_id,
        query,
        [memory["memory"] for memory in relevant],
    )
    return relevant
