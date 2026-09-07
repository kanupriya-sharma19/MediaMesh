from datetime import date
from typing import Any

from agent.llm_agent import LLMAgent


class FakeMCPClient:
    def __init__(self, responses: dict[tuple[str, str], dict[str, Any]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def call(self, server: str, tool: str, **arguments: Any) -> dict[str, Any]:
        self.calls.append((server, tool, arguments))
        return self.responses[(server, tool)]


class FakeAnswerModel:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.evidence: list[dict[str, Any]] = []

    def answer(self, query: str, evidence: dict[str, Any]) -> str:
        self.queries.append(query)
        self.evidence.append(evidence)
        return "Grounded LLM answer"


def responses() -> dict[tuple[str, str], dict[str, Any]]:
    return {
        ("MusicBrainz", "search_recordings"): {
            "recordings": [
                {
                    "recording_id": "recording-1",
                    "release_dates": ["2026-09-07"],
                }
            ]
        },
        ("MusicBrainz", "get_recording"): {
            "recording_id": "recording-1",
            "title": "Indie Song",
            "release_dates": ["2026-09-07"],
            "relations": [],
        },
        ("TMDB", "search_movies"): {
            "movies": [{"movie_id": 101, "release_date": "2026-09-01"}]
        },
        ("TMDB", "get_movie"): {
            "movie_id": 101,
            "title": "A24 Film",
            "release_date": "2026-09-01",
            "production_companies": [{"name": "A24"}],
        },
        ("TMDB", "get_movie_credits"): {"crew": []},
    }


def test_llm_agent_calls_mcp_and_returns_model_answer_without_graph() -> None:
    client = FakeMCPClient(responses())
    model = FakeAnswerModel()

    result = LLMAgent(client, model, today=date(2026, 9, 7)).run(
        "Find indie-pop songs connected to recent A24 films"
    )

    assert result["answer"] == "Grounded LLM answer"
    assert "graph" not in result
    assert "connections" not in result
    assert model.evidence[0]["music"][0]["title"] == "Indie Song"
    assert model.evidence[0]["films"][0]["movie"]["title"] == "A24 Film"


def test_capability_query_uses_catalog_without_calling_mcp() -> None:
    client = FakeMCPClient({})
    model = FakeAnswerModel()

    result = LLMAgent(client, model).run("What tools do you have?")

    assert result["answer"] == "Grounded LLM answer"
    assert client.calls == []
    assert "TMDB" in model.evidence[0]["tools"]
    assert "MusicBrainz" in model.evidence[0]["tools"]
