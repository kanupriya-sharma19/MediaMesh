from __future__ import annotations

from typing import Any

from backend.mcp_servers.tmdb_mcp import TMDBClient, get_movie, get_movie_credits


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    def __init__(self) -> None:
        self.get_calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.get_calls.append({"url": url, **kwargs})
        if url.endswith("/movie/123/credits"):
            return FakeResponse(
                200,
                {
                    "cast": [
                        {
                            "id": 20,
                            "name": "Lead Actor",
                            "character": "Alex",
                            "order": 0,
                        }
                    ],
                    "crew": [
                        {
                            "id": 10,
                            "name": "Music Supervisor",
                            "department": "Sound",
                            "job": "Music Supervisor",
                        }
                    ],
                },
            )
        if url.endswith("/movie/123"):
            return FakeResponse(
                200,
                {
                    "id": 123,
                    "title": "A24 Example",
                    "release_date": "2026-09-01",
                    "overview": "A structured movie response.",
                    "poster_path": "/poster.jpg",
                    "production_companies": [
                        {"id": 1234, "name": "A24", "origin_country": "US"}
                    ],
                },
            )
        return FakeResponse(
            200,
            {
                "results": [
                    {
                        "id": 123,
                        "title": "A24 Example",
                        "release_date": "2026-09-01",
                        "overview": "A search result.",
                        "poster_path": None,
                    }
                ]
            },
        )


def test_get_movie_preserves_structured_production_company() -> None:
    session = FakeSession()
    client = TMDBClient("test-key", session=session)

    result = client.get_movie(123)

    assert result["movie_id"] == 123
    assert result["title"] == "A24 Example"
    assert result["poster_url"] == "https://image.tmdb.org/t/p/w500/poster.jpg"
    assert result["production_companies"] == [
        {"company_id": 1234, "name": "A24", "origin_country": "US"}
    ]
    assert session.get_calls[0]["params"]["api_key"] == "test-key"


def test_get_movie_credits_preserves_crew_relationship_fields() -> None:
    client = TMDBClient("test-key", session=FakeSession())

    result = client.get_movie_credits(123)

    assert result["crew"] == [
        {
            "person_id": 10,
            "name": "Music Supervisor",
            "department": "Sound",
            "job": "Music Supervisor",
        }
    ]
    assert result["cast"][0]["name"] == "Lead Actor"


def test_invalid_movie_id_is_rejected_by_mcp_tool() -> None:
    result = get_movie(0)

    assert result == {"error": "TMDB movie ID must be a positive integer"}


def test_invalid_credit_movie_id_is_rejected_by_mcp_tool() -> None:
    result = get_movie_credits(-1)

    assert result == {"error": "TMDB movie ID must be a positive integer"}
