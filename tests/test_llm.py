from typing import Any

from agent.llm import GeminiAnswerModel, LLMError


def test_gemini_answer_model_uses_langchain_model(monkeypatch: Any) -> None:
    class FakeChatModel:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

        def invoke(self, prompt: str) -> Any:
            return type("Response", (), {"content": "Answer from Gemini"})()

    monkeypatch.setattr("agent.llm.ChatGoogleGenerativeAI", FakeChatModel)
    model = GeminiAnswerModel("test-key", "gemini-test")

    assert (
        model.answer("Find connections", {"music": [], "films": []})
        == "Answer from Gemini"
    )
    assert model.model.kwargs["model"] == "gemini-test"


def test_gemini_answer_model_wraps_provider_errors(monkeypatch: Any) -> None:
    class FailingChatModel:
        def __init__(self, **kwargs: Any) -> None:
            pass

        def invoke(self, prompt: str) -> Any:
            raise RuntimeError("quota exceeded")

    monkeypatch.setattr("agent.llm.ChatGoogleGenerativeAI", FailingChatModel)
    model = GeminiAnswerModel("test-key")
    try:
        model.answer("Find connections", {})
    except LLMError as exc:
        assert "quota exceeded" in str(exc)
    else:
        raise AssertionError("Expected LLMError")
