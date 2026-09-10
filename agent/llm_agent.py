"""Dynamic LLM-backed MCP agent."""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Any, Protocol

from agent.llm import AnswerModel, GeminiAnswerModel, LLMError
from langchain_core.messages import BaseMessage
from utils.config import load_settings


logger = logging.getLogger(__name__)
MAX_STEPS = 10


class AgentError(RuntimeError):
    """Raised for invalid actions or unusable MCP responses."""


class MCPToolClient(Protocol):
    """MCP client boundary used by the agent."""

    def call(self, server: str, tool: str, **arguments: Any) -> dict[str, Any]:
        """Execute an MCP tool."""
        ...

    def list_all_tools(self) -> list[dict[str, Any]]:
        """Discover all available MCP tools."""
        ...


class LLMAgent:
    """Discover MCP tools, let Gemini select them, and synthesize an answer."""

    def __init__(
        self,
        mcp_client: MCPToolClient,
        answer_model: AnswerModel | None = None,
    ) -> None:
        self.mcp_client = mcp_client
        self.answer_model = answer_model or _model_from_environment()

    def run(
        self,
        query: str,
        chat_history: Sequence[BaseMessage] | None = None,
    ) -> dict[str, Any]:
        """Run the bounded dynamic MCP agent loop."""
        if not query.strip():
            raise AgentError("Please enter a media relationship query.")
        logger.info("User query received: %s", query)
        try:
            tools = self.mcp_client.list_all_tools()
        except Exception as exc:
            raise AgentError(f"MCP tool discovery failed: {exc}") from exc

        known_tools = {
            (tool.get("server"), tool.get("name"))
            for tool in tools
            if isinstance(tool, dict)
        }
        evidence: list[dict[str, Any]] = []
        warnings: list[str] = []
        executed_calls: set[str] = set()

        for step in range(MAX_STEPS):
            logger.info("Agent step %s", step + 1)
            try:
                if chat_history:
                    action = self.answer_model.next_action(
                        query=query,
                        tools=tools,
                        evidence=evidence,
                        chat_history=chat_history,
                    )
                else:
                    action = self.answer_model.next_action(
                        query=query, tools=tools, evidence=evidence
                    )
            except LLMError as exc:
                raise AgentError(str(exc)) from exc

            action_type = action.get("type")
            if action_type == "final":
                answer = action.get("answer")
                if not isinstance(answer, str):
                    raise AgentError("Agent returned an invalid final answer.")
                return {"answer": answer, "warnings": warnings, "sources": evidence}
            if action_type != "tool_call":
                raise AgentError(f"Agent returned unknown action type: {action_type}")

            server = action.get("server")
            tool = action.get("tool")
            arguments = action.get("arguments", {})
            if not isinstance(server, str):
                raise AgentError("Agent returned invalid server.")
            if not isinstance(tool, str):
                raise AgentError("Agent returned invalid tool.")
            if not isinstance(arguments, dict):
                raise AgentError("Agent returned invalid tool arguments.")
            if (server, tool) not in known_tools:
                raise AgentError(f"Agent selected undiscovered tool: {server}.{tool}")

            call_key = f"{server}:{tool}:{json.dumps(arguments, sort_keys=True)}"
            if call_key in executed_calls:
                warnings.append(f"Duplicate tool call prevented: {server}.{tool}")
                logger.warning("Duplicate call prevented: %s.%s", server, tool)
                continue
            executed_calls.add(call_key)

            logger.info("Calling %s.%s with %s", server, tool, arguments)
            try:
                result = self._call(server, tool, **arguments)
            except AgentError as exc:
                warnings.append(str(exc))
                evidence.append(
                    {
                        "type": "tool_error",
                        "server": server,
                        "tool": tool,
                        "arguments": arguments,
                        "error": str(exc),
                    }
                )
                continue
            evidence.append(
                {
                    "type": "tool_result",
                    "server": server,
                    "tool": tool,
                    "arguments": arguments,
                    "result": result,
                }
            )

        raise AgentError(f"Agent exceeded maximum of {MAX_STEPS} steps.")

    def _call(self, server: str, tool: str, **arguments: Any) -> dict[str, Any]:
        response = self.mcp_client.call(server, tool, **arguments)
        if not isinstance(response, dict):
            raise AgentError(f"{server} {tool} returned a malformed response.")
        if response.get("error"):
            raise AgentError(f"{server} {tool} failed: {response['error']}")
        return response


def _model_from_environment() -> AnswerModel:
    settings = load_settings()
    if not settings.gemini_api_key:
        raise AgentError(
            "GOOGLE_API_KEY or GEMINI_API_KEY is missing. Add it to .env to enable Gemini answers."
        )
    return GeminiAnswerModel(settings.gemini_api_key, settings.gemini_model)
