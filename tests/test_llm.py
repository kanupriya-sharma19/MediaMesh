from typing import Any

from agent.llm import GeminiAnswerModel, _parse_action


def test_gemini_next_action_accepts_dynamic_tools(monkeypatch: Any) -> None:
    class FakeChatModel:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        def invoke(self, prompt: str) -> Any:
            assert '"name": "search_books"' in prompt
            return type(
                "Response",
                (),
                {
                    "content": """```json
{"type":"tool_call","server":"GoogleBooks","tool":"search_books","arguments":{"query":"Pride and Prejudice"}}
```"""
                },
            )()

    monkeypatch.setattr("agent.llm.ChatGoogleGenerativeAI", FakeChatModel)
    model = GeminiAnswerModel("test-key", "gemini-test")

    action = model.next_action(
        "Find Pride and Prejudice",
        [
            {
                "server": "GoogleBooks",
                "name": "search_books",
                "description": "Find books",
                "input_schema": {"type": "object"},
            }
        ],
        [],
    )

    assert action["tool"] == "search_books"


def test_parse_action_accepts_fenced_json() -> None:
    assert _parse_action('```json\n{"type":"final","answer":"Done"}\n```') == {
        "type": "final",
        "answer": "Done",
    }
