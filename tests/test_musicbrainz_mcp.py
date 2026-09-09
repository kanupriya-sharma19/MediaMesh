from __future__ import annotations

from typing import Any

from mcp_servers.musicbrainz_mcp import (
    MusicBrainzClient,
    MusicBrainzAPIError,
    get_recording,
)


class FakeResponse:
    def __init__(
        self, status_code: int, payload: dict[str, Any], text: str = ""
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    def __init__(self) -> None:
        self.get_calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.get_calls.append({"url": url, **kwargs})
        if "/recording/recording-1" in url:
            return FakeResponse(
                200,
                {
                    "id": "recording-1",
                    "title": "Test Song",
                    "length": 210000,
                    "artist-credit": [
                        {"artist": {"id": "artist-1", "name": "Artist A"}}
                    ],
                    "releases": [{"date": "2026-09-07"}],
                    "relations": [
                        {
                            "type": "composer",
                            "direction": "forward",
                            "artist": {"id": "artist-2", "name": "Composer B"},
                        }
                    ],
                },
            )
        return FakeResponse(
            200,
            {
                "recordings": [
                    {
                        "id": "recording-1",
                        "title": "Test Song",
                        "artist-credit": [
                            {"artist": {"id": "artist-1", "name": "Artist A"}}
                        ],
                    }
                ],
                "artists": [
                    {
                        "id": "artist-1",
                        "name": "Artist A",
                        "sort-name": "A, Artist",
                    }
                ],
            },
        )


def test_search_recordings_returns_normalized_metadata_and_user_agent() -> None:
    session = FakeSession()
    client = MusicBrainzClient(session=session, min_request_interval=0)

    result = client.search_recordings('recording:"Test Song"')

    assert result[0]["recording_id"] == "recording-1"
    assert result[0]["artists"] == [
        {"artist_id": "artist-1", "artist_name": "Artist A"}
    ]
    assert session.get_calls[0]["params"] == {
        "query": 'recording:"Test Song"',
        "limit": 25,
        "fmt": "json",
    }
    assert session.get_calls[0]["headers"]["User-Agent"].startswith("MediaMesh/")


def test_get_recording_preserves_release_and_explicit_relations() -> None:
    client = MusicBrainzClient(session=FakeSession(), min_request_interval=0)

    result = client.get_recording("recording-1")

    assert result["release_dates"] == ["2026-09-07"]
    assert result["relations"] == [
        {
            "type": "composer",
            "direction": "forward",
            "target_id": "artist-2",
            "target_name": "Composer B",
        }
    ]


def test_empty_recording_id_is_rejected_by_mcp_tool() -> None:
    assert get_recording("") == {"error": "MusicBrainz recording ID cannot be empty"}


def test_rate_limit_is_reported() -> None:
    class RateLimitedSession(FakeSession):
        def get(self, url: str, **kwargs: Any) -> FakeResponse:
            return FakeResponse(429, {}, "Too many requests")

    client = MusicBrainzClient(session=RateLimitedSession(), min_request_interval=0)
    try:
        client.search_recordings("test")
    except MusicBrainzAPIError as exc:
        assert "rate limit" in str(exc).lower()
    else:
        raise AssertionError("Expected MusicBrainzAPIError")
