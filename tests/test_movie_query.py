from datetime import date
from typing import Any

from agent.llm_agent import LLMAgent


class FakeMCPClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def call(self, server: str, tool: str, **arguments: Any) -> dict[str, Any]:
        self.calls.append((server, tool, arguments))
        if tool == "search_movies":
            return {"movies": [{"movie_id": 777, "title": "Bahubali: The Beginning"}]}
        if tool == "get_movie":
            return {
                "movie_id": 777,
                "title": "Bahubali: The Beginning",
                "release_date": "2015-07-10",
                "overview": "An epic historical action film.",
                "production_companies": [],
            }
        if tool == "get_movie_credits":
            return {"cast": [], "crew": []}
        raise AssertionError(f"Unexpected MCP call: {server}.{tool}")


class FakeGemini:
    def __init__(self) -> None:
        self.evidence: dict[str, Any] | None = None

    def answer(self, query: str, evidence: dict[str, Any]) -> str:
        self.evidence = evidence
        return "Bahubali: The Beginning was released in 2015."


def test_movie_query_uses_tmdb_mcp_and_gemini_without_graph() -> None:
    mcp = FakeMCPClient()
    gemini = FakeGemini()

    result = LLMAgent(mcp, gemini, today=date(2026, 9, 7)).run(
        'Tell me about movie "Bahubali I"'
    )

    assert result["answer"].startswith("Bahubali")
    assert "graph" not in result
    assert "connections" not in result
    assert [tool for _, tool, _ in mcp.calls] == [
        "search_movies",
        "get_movie",
        "get_movie_credits",
    ]
    assert mcp.calls[0][2] == {"query": "Bahubali I"}
    assert gemini.evidence["films"][0]["movie"]["title"] == "Bahubali: The Beginning"
