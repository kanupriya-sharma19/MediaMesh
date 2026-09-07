"""LLM-backed agent that answers from MusicBrainz and TMDB MCP evidence."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import logging
import re
from typing import Any, Protocol

from agent.llm import TOOL_CATALOG, AnswerModel, GeminiAnswerModel, LLMError
from utils.config import load_settings


logger = logging.getLogger(__name__)


class AgentError(RuntimeError):
    """Raised for invalid queries or unusable MCP responses."""


class MCPToolClient(Protocol):
    """MCP client boundary used by the LLM agent."""

    def call(self, server: str, tool: str, **arguments: Any) -> dict[str, Any]:
        """Call a named MCP tool."""
        ...


class LLMAgent:
    """Call MCP tools, then ask an LLM to synthesize the returned evidence."""

    def __init__(
        self,
        mcp_client: MCPToolClient,
        answer_model: AnswerModel | None = None,
        today: date | None = None,
    ) -> None:
        self.mcp_client = mcp_client
        self.today = today or datetime.now(timezone.utc).date()
        self.answer_model = answer_model or _model_from_environment()

    def run(self, query: str) -> dict[str, Any]:
        """Retrieve source evidence and return an LLM-generated answer."""
        if not query.strip():
            raise AgentError("Please enter a media relationship query.")
        logger.info("User query received")
        evidence: dict[str, Any] = {"music": [], "films": []}
        warnings: list[str] = []
        if _is_capability_query(query):
            evidence["tools"] = TOOL_CATALOG
        elif _is_movie_query(query):
            self._collect_movie(evidence, query)
        else:
            self._collect_music(evidence, warnings)
            self._collect_films(evidence, warnings)
        try:
            answer = self.answer_model.answer(query, evidence)
        except LLMError as exc:
            raise AgentError(str(exc)) from exc
        return {
            "answer": answer,
            "warnings": warnings,
            "sources": evidence,
        }

    def _collect_music(self, evidence: dict[str, Any], warnings: list[str]) -> None:
        logger.info("Calling MusicBrainz search_recordings")
        response = self._call("MusicBrainz", "search_recordings", query="tag:indie-pop")
        recordings = response.get("recordings")
        if not isinstance(recordings, list):
            raise AgentError("MusicBrainz returned an invalid recordings list.")
        for result in recordings:
            if not isinstance(result, dict):
                continue
            if not _has_this_week_release(result.get("release_dates"), self.today):
                continue
            recording_id = result.get("recording_id")
            if not isinstance(recording_id, str) or not recording_id:
                warnings.append("MusicBrainz returned a recording without a valid ID.")
                continue
            evidence["music"].append(
                self._call("MusicBrainz", "get_recording", recording_id=recording_id)
            )

    def _collect_films(self, evidence: dict[str, Any], warnings: list[str]) -> None:
        logger.info("Calling TMDB search_movies")
        response = self._call("TMDB", "search_movies", query="A24")
        movies = response.get("movies")
        if not isinstance(movies, list):
            raise AgentError("TMDB returned an invalid movies list.")
        for result in movies:
            if not isinstance(result, dict):
                continue
            movie_id = result.get("movie_id")
            if not isinstance(movie_id, int) or not _is_recent(
                result.get("release_date"), self.today
            ):
                continue
            movie = self._call("TMDB", "get_movie", movie_id=movie_id)
            if not _is_a24_movie(movie):
                continue
            evidence["films"].append(
                {
                    "movie": movie,
                    "credits": self._call(
                        "TMDB", "get_movie_credits", movie_id=movie_id
                    ),
                }
            )

    def _collect_movie(self, evidence: dict[str, Any], query: str) -> None:
        title = _movie_title(query)
        logger.info("Calling TMDB search_movies for %s", title)
        response = self._call("TMDB", "search_movies", query=title)
        movies = response.get("movies")
        if not isinstance(movies, list) or not movies:
            raise AgentError(f"TMDB found no movie results for '{title}'.")
        movie_result = next((item for item in movies if isinstance(item, dict)), None)
        movie_id = movie_result.get("movie_id") if movie_result else None
        if not isinstance(movie_id, int):
            raise AgentError(f"TMDB returned no valid movie ID for '{title}'.")
        movie = self._call("TMDB", "get_movie", movie_id=movie_id)
        evidence["films"].append(
            {
                "movie": movie,
                "credits": self._call("TMDB", "get_movie_credits", movie_id=movie_id),
            }
        )

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


def _is_movie_query(query: str) -> bool:
    return bool(re.search(r"\b(movie|film)\b", query, re.IGNORECASE))


def _is_capability_query(query: str) -> bool:
    return bool(
        re.search(
            r"\b(tools?|capabilit(?:y|ies)|mcp|what can you|available)\b",
            query,
            re.IGNORECASE,
        )
    )


def _movie_title(query: str) -> str:
    match = re.search(r"\b(?:movie|film)\s+[\"']?(.+?)[\"']?$", query, re.IGNORECASE)
    if match:
        return match.group(1).strip(" \"'")
    return query.strip()


def _is_recent(value: Any, today: date) -> bool:
    parsed = _parse_date(value)
    return parsed is not None and today - timedelta(days=365) <= parsed <= today


def _has_this_week_release(values: Any, today: date) -> bool:
    if not isinstance(values, list):
        return False
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return any(
        (parsed := _parse_date(value)) is not None and start <= parsed <= end
        for value in values
    )


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _is_a24_movie(movie: dict[str, Any]) -> bool:
    companies = movie.get("production_companies", [])
    return isinstance(companies, list) and any(
        isinstance(company, dict)
        and isinstance(company.get("name"), str)
        and company["name"].casefold() == "a24"
        for company in companies
    )
