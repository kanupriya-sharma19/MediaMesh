"""Adapter that reuses the existing MediaMesh chat logic."""

from __future__ import annotations

from typing import Any

from backend.agent.llm_agent import LLMAgent
from backend.agent.mcp_client import StdioMCPClient
from langchain_core.messages import AIMessage, HumanMessage
from backend.memory.chat_history import (
    clear_chat_history,
    get_chat_history,
    save_chat_history,
)


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

    def ask(
        self, user_id: str, query: str, session_id: str = "default"
    ) -> dict[str, Any]:
        history = get_chat_history(user_id, session_id)
        history.append(HumanMessage(content=query))
        result = self.agent.run(query, chat_history=history)
        history.append(AIMessage(content=result.get("answer", "")))
        save_chat_history(user_id, history, session_id)
        return result


def _serialize_message(message: Any) -> dict[str, Any]:
    if isinstance(message, HumanMessage):
        return {"role": "user", "content": str(message.content)}
    if isinstance(message, AIMessage):
        return {"role": "assistant", "content": str(message.content)}
    return {"role": "assistant", "content": str(message.content)}
