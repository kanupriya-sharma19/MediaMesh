from typing import Any

from mcp_servers.books_mcp import GoogleBooksClient, get_book


class FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def json(self) -> dict[str, Any]:
        return self.payload


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return FakeResponse(
            {
                "items": [
                    {
                        "id": "book-1",
                        "volumeInfo": {
                            "title": "Test Book",
                            "authors": ["Author A"],
                            "publishedDate": "2020-01-01",
                            "description": "A test book.",
                            "imageLinks": {
                                "thumbnail": "https://example.test/book.jpg"
                            },
                        },
                    }
                ]
            }
        )


def test_search_books_returns_normalized_metadata() -> None:
    session = FakeSession()
    client = GoogleBooksClient(api_key="test-key", session=session)

    result = client.search_books("test book")

    assert result[0]["book_id"] == "book-1"
    assert result[0]["title"] == "Test Book"
    assert result[0]["authors"] == ["Author A"]
    assert session.calls[0]["params"]["key"] == "test-key"


def test_empty_book_id_is_rejected_by_mcp_tool() -> None:
    assert get_book("") == {"error": "Google Books book ID cannot be empty"}
