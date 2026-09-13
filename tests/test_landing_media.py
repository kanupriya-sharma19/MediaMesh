from dataclasses import dataclass

from backend.services import landing_media


@dataclass
class FakeSettings:
    tmdb_api_key: str | None = "tmdb-key"
    google_books_api_key: str | None = None


class FailingMovies:
    def __init__(self, api_key: str) -> None:
        pass

    def search_movies(self, query: str) -> list[dict[str, str]]:
        raise RuntimeError("TMDB unavailable")


class FakeMusic:
    def search_recordings(self, query: str) -> list[dict[str, str]]:
        return [{"title": "A Record", "cover_url": "https://example.test/music.jpg"}]


class FakeBooks:
    def __init__(self, api_key: str | None) -> None:
        pass

    def search_books(self, query: str) -> list[dict[str, str]]:
        return [{"title": "A Book", "thumbnail": "https://example.test/book.jpg"}]


def test_landing_media_keeps_available_sources_and_caches_result(monkeypatch) -> None:
    landing_media._cache = None
    landing_media._cache_expires_at = 0
    monkeypatch.setattr(landing_media, "load_settings", lambda: FakeSettings())
    monkeypatch.setattr(landing_media, "TMDBClient", FailingMovies)
    monkeypatch.setattr(landing_media, "MusicBrainzClient", FakeMusic)
    monkeypatch.setattr(landing_media, "GoogleBooksClient", FakeBooks)

    result = landing_media.get_landing_media()
    cached_result = landing_media.get_landing_media()

    assert result == cached_result
    assert result["movies"] == []
    assert result["music"][0]["type"] == "music"
    assert result["books"][0]["type"] == "book"
