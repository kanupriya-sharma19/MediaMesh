from typing import Any

from backend.agent.llm_agent import LLMAgent


class FakeMCPClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def list_all_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "server": "GoogleBooks",
                "name": "search_books",
                "description": "Find books",
                "input_schema": {"type": "object"},
            }
        ]

    def call(self, server: str, tool: str, **arguments: Any) -> dict[str, Any]:
        self.calls.append((server, tool, arguments))
        return {"books": [{"book_id": "book-1", "title": "Pride and Prejudice"}]}


class FakeAnswerModel:
    def __init__(self) -> None:
        self.tools: list[dict[str, Any]] | None = None
        self.actions = [
            {
                "type": "tool_call",
                "server": "GoogleBooks",
                "tool": "search_books",
                "arguments": {"query": "Pride and Prejudice"},
            },
            {"type": "final", "answer": "Found the book."},
        ]

    def next_action(
        self,
        query: str,
        tools: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self.tools = tools
        return self.actions.pop(0)


def test_agent_discovers_tools_passes_them_to_model_and_executes_call() -> None:
    client = FakeMCPClient()
    model = FakeAnswerModel()

    result = LLMAgent(client, model).run("Tell me about Pride and Prejudice")

    assert result["answer"] == "Found the book."
    assert model.tools == client.list_all_tools()
    assert client.calls == [
        ("GoogleBooks", "search_books", {"query": "Pride and Prejudice"})
    ]


def test_agent_rejects_undiscovered_tool() -> None:
    client = FakeMCPClient()

    class InvalidModel(FakeAnswerModel):
        def next_action(
            self,
            query: str,
            tools: list[dict[str, Any]],
            evidence: list[dict[str, Any]],
        ) -> dict[str, Any]:
            return {
                "type": "tool_call",
                "server": "Unknown",
                "tool": "missing",
                "arguments": {},
            }

    try:
        LLMAgent(client, InvalidModel()).run("test")
    except Exception as exc:
        assert "undiscovered tool" in str(exc)
    else:
        raise AssertionError("Expected undiscovered-tool validation error")
