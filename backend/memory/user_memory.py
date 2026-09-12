"""PostgreSQL-backed, user-scoped long-term preference memory."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from backend.database import UserMemory, session_scope

logger = logging.getLogger(__name__)

_NAME_PATTERNS = (
    re.compile(
        r"\bmy\s+name\s+is\s+([A-Za-z][A-Za-z'-]{1,39}(?:\s+[A-Za-z][A-Za-z'-]{1,39}){0,2})\b[.!?]?\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bI(?:\s+am|'m)\s+([A-Za-z][A-Za-z'-]{1,39}(?:\s+[A-Za-z][A-Za-z'-]{1,39}){0,2})\b[.!?]?\s*$",
        re.IGNORECASE,
    ),
)
_PREFERENCE_PATTERNS = (
    re.compile(
        r"\bI\s+(?:really\s+)?(?:like|love|enjoy|prefer)\s+(.+?)[.!?]?\s*$",
        re.IGNORECASE,
    ),
    re.compile(r"\bmy\s+favorite\s+([^.!?]+?)\s+is\s+(.+?)[.!?]?\s*$", re.IGNORECASE),
    re.compile(r"\bI\s+(?:don't|do not|dislike|hate)\s+(.+?)[.!?]?\s*$", re.IGNORECASE),
)


def extract_memory(message: str) -> tuple[str, str] | None:
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
    now = datetime.now(UTC)
    with session_scope() as session:
        existing = session.scalar(
            select(UserMemory).where(
                UserMemory.user_id == user_id, UserMemory.memory == memory.strip()
            )
        )
        if existing:
            existing.updated_at = now
            existing.category = category
        else:
            session.add(
                UserMemory(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    memory=memory.strip(),
                    category=category,
                    created_at=now,
                    updated_at=now,
                )
            )
    logger.info(
        "[MEMORY SAVED] user_id=%s category=%s memory=%s", user_id, category, memory
    )


def get_user_memories(user_id: str, limit: int = 12) -> list[dict[str, str]]:
    with session_scope() as session:
        rows = session.scalars(
            select(UserMemory)
            .where(UserMemory.user_id == user_id)
            .order_by(UserMemory.updated_at.desc())
            .limit(limit)
        ).all()
    return [_memory_dict(row) for row in rows]


def get_relevant_memories(
    user_id: str, query: str, limit: int = 8
) -> list[dict[str, str]]:
    memories = get_user_memories(user_id, limit=100)
    terms = {
        term.lower() for term in re.findall(r"[a-zA-Z0-9]+", query) if len(term) > 2
    }
    scored = []
    recommendation = re.search(
        r"\b(recommend|suggest|like|similar|favorite)\b", query, re.IGNORECASE
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


def _memory_dict(row: UserMemory) -> dict[str, str]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "memory": row.memory,
        "category": row.category,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }
