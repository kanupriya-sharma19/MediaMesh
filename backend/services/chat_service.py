"""Adapter that reuses the existing MediaMesh chat logic."""

from __future__ import annotations

import logging
from typing import Any

from backend.agent.llm_agent import LLMAgent
from backend.agent.mcp_client import StdioMCPClient
from backend.memory.chat_history import (
    clear_chat_history,
    create_chat_session,
    get_chat_history,
    get_conversation_summary,
    get_chat_sessions,
    save_conversation_summary,
    save_chat_history,
    summarize_messages,
)
from backend.memory.user_memory import (
    extract_memory,
    get_relevant_memories,
    save_memory,
)
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


MAX_RECENT_MESSAGES = 20
SUMMARY_TRIGGER = 24
logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self) -> None:
        self._agent: LLMAgent | None = None

    @property
    def agent(self) -> LLMAgent:
        if self._agent is None:
            self._agent = LLMAgent(StdioMCPClient())
        return self._agent

    def history(
        self, user_id: str, session_id: str = "default"
    ) -> list[dict[str, Any]]:
        return [
            _serialize_message(message)
            for message in get_chat_history(user_id, session_id)
        ]

    def clear(self, user_id: str, session_id: str = "default") -> None:
        clear_chat_history(user_id, session_id)

    def create_session(self, user_id: str) -> dict[str, str]:
        return create_chat_session(user_id)

    def sessions(self, user_id: str) -> list[dict[str, str]]:
        return get_chat_sessions(user_id)

    def ask(
        self, user_id: str, query: str, session_id: str = "default"
    ) -> dict[str, Any]:
        history = get_chat_history(user_id, session_id)
        extracted = extract_memory(query)
        if extracted:
            save_memory(user_id, *extracted)
        memories = get_relevant_memories(user_id, query)
        logger.info(
            "[MEMORY RETRIEVED] user_id=%s session_id=%s count=%s",
            user_id,
            session_id,
            len(memories),
        )
        history_with_query = [*history, HumanMessage(content=query)]
        context_history = _build_context_history(
            history_with_query,
            get_conversation_summary(user_id, session_id),
            memories,
        )
        logger.info(
            "[GEMINI CONTEXT] user_id=%s session_id=%s context=%s",
            user_id,
            session_id,
            context_history[0].content,
        )
        result = self.agent.run(query, chat_history=context_history)
        history_with_query.append(AIMessage(content=result.get("answer", "")))
        save_chat_history(user_id, history_with_query, session_id)
        if len(history_with_query) > SUMMARY_TRIGGER:
            save_conversation_summary(
                user_id,
                session_id,
                summarize_messages(history_with_query[:-MAX_RECENT_MESSAGES]),
            )
        return result


def _build_context_history(
    history: list[Any], summary: str | None, memories: list[dict[str, str]]
) -> list[Any]:
    context_parts = [
        "Relevant long-term user memories:",
        *(f"- {memory['memory']}" for memory in memories),
    ]
    if summary:
        context_parts.extend(["Conversation summary:", summary])
    return [
        SystemMessage(content="\n".join(context_parts)),
        *history[-MAX_RECENT_MESSAGES:],
    ]


def _serialize_message(message: Any) -> dict[str, Any]:
    if isinstance(message, HumanMessage):
        return {"role": "user", "content": str(message.content)}
    if isinstance(message, AIMessage):
        return {"role": "assistant", "content": str(message.content)}
    return {"role": "assistant", "content": str(message.content)}
