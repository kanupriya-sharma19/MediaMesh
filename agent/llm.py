"""LLM adapter for dynamic MCP tool selection."""

from __future__ import annotations

import json
from typing import Any, Protocol

from langchain_google_genai import ChatGoogleGenerativeAI


class LLMError(RuntimeError):
    """Raised when the configured LLM cannot generate an action."""


class AnswerModel(Protocol):
    """Interface used by the agent to choose MCP actions."""

    def next_action(
        self,
        query: str,
        tools: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Decide whether to call a discovered tool or return a final answer."""
        ...


SYSTEM_PROMPT = """
You are SonicGraph, a dynamic media intelligence agent.

Choose only from the tools listed in AVAILABLE TOOLS. The MCP servers are the
source of truth for tool names, descriptions, and input schemas. Do not invent
facts, tools, arguments, or relationships.

Use the minimum number of relevant tool calls. Search before detail calls when
an ID is required, reuse IDs from previous results, and never repeat an
identical call. If the evidence is sufficient, return a final answer.

Return ONLY valid JSON in one of these forms:
{"type":"tool_call","server":"...","tool":"...","arguments":{}}
{"type":"final","answer":"..."}
"""


class GeminiAnswerModel:
    """Gemini model used as the dynamic MCP decision-maker."""

    def __init__(self, api_key: str, model: str = "gemini-3.5-flash-lite") -> None:
        self.model = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0,
        )

    def next_action(
        self,
        query: str,
        tools: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
    ) -> dict[str, Any]:
        prompt = f"""
{SYSTEM_PROMPT}

AVAILABLE TOOLS:
{json.dumps(tools, indent=2, default=str)}

USER QUERY:
{query}

PREVIOUS TOOL RESULTS:
{json.dumps(evidence, indent=2, default=str)}

Decide the next action.
"""
        try:
            response = self.model.invoke(prompt)
            content = response.content
        except Exception as exc:
            raise LLMError(f"Gemini request failed: {exc}") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMError("Gemini returned an empty response.")
        try:
            return _parse_action(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"Gemini returned invalid JSON: {content}") from exc


def _parse_action(content: str) -> dict[str, Any]:
    """Parse Gemini JSON with tolerant Markdown-fence handling."""
    candidate = content.strip()
    if candidate.startswith("```") and candidate.endswith("```"):
        lines = candidate.splitlines()
        candidate = "\n".join(lines[1:-1]).strip()
    try:
        action = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            raise
        action = json.loads(candidate[start : end + 1])
    if not isinstance(action, dict):
        raise json.JSONDecodeError("Action must be a JSON object", candidate, 0)
    return action
