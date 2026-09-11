from typing import Any

from backend.agent.llm import GeminiAnswerModel, _parse_action
from langchain_core.messages import SystemMessage


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

    monkeypatch.setattr("backend.agent.llm.ChatGoogleGenerativeAI", FakeChatModel)
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


def test_gemini_prompt_contains_long_term_memory(monkeypatch: Any) -> None:
    class FakeChatModel:
        def __init__(self, **kwargs: Any) -> None:
            self.prompt = ""

        def invoke(self, prompt: str) -> Any:
            self.prompt = prompt
            return type(
                "Response",
                (),
                {"content": '{"type":"final","answer":"Kanupriya"}'},
            )()

    fake_model = FakeChatModel()
    monkeypatch.setattr(
        "backend.agent.llm.ChatGoogleGenerativeAI", lambda **kwargs: fake_model
    )
    model = GeminiAnswerModel("test-key", "gemini-test")

    model.next_action(
        "What is my name?",
        [],
        [],
        chat_history=[
            SystemMessage(
                content="Relevant long-term user memories:\n- User's name is Kanupriya"
            )
        ],
    )

    assert "User's name is Kanupriya" in fake_model.prompt
