"""LLM adapter for grounded answers over MCP results."""

from __future__ import annotations

import json
from typing import Any, Protocol

from langchain_google_genai import ChatGoogleGenerativeAI


TOOL_CATALOG = {
    "TMDB": {
        "search_movies": "Find movies by title or keywords.",
        "get_movie": "Retrieve structured movie metadata and production companies.",
        "get_movie_credits": "Retrieve cast and crew credits for a movie.",
    },
    "MusicBrainz": {
        "search_recordings": "Find music recordings by title, artist, or MusicBrainz query.",
        "get_recording": "Retrieve recording metadata, artists, releases, and explicit relations.",
        "search_artists": "Find music artists.",
        "get_artist": "Retrieve artist metadata and explicit relations.",
    },
}


class LLMError(RuntimeError):
    """Raised when the configured LLM cannot generate an answer."""


class AnswerModel(Protocol):
    """Interface used by the agent to synthesize MCP evidence."""

    def answer(self, query: str, evidence: dict[str, Any]) -> str:
        """Generate a grounded answer from the supplied evidence."""
        ...


class GeminiAnswerModel:
    """LangChain adapter for Google's Gemini free-tier models."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self.model = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0,
        )

    def answer(self, query: str, evidence: dict[str, Any]) -> str:
        prompt = (
            "You are SonicGraph, a general media research assistant. Answer the user's query "
            "using the MCP evidence below. The evidence may include a tool catalog describing "
            "available capabilities. Explain those capabilities when asked. Never invent facts "
            "or relationships; if evidence is missing, say what is missing. Mention sources "
            "for important claims.\n\n"
            f"User query:\n{query}\n\nMCP evidence:\n"
            f"{json.dumps(evidence, ensure_ascii=True, indent=2)}"
        )
        try:
            response = self.model.invoke(prompt)
            content = response.content
        except Exception as exc:
            raise LLMError(f"Gemini request failed: {exc}") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMError("LLM returned an empty answer")
        return content.strip()
