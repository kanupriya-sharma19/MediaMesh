from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from backend.memory.chat_history import clear_chat_history, get_chat_history
from backend.memory.user_memory import get_user_memories
from backend.memory.user_memory import extract_memory
from backend.services.chat_service import ChatService


class FakeAgent:
    def __init__(self) -> None:
        self.histories: list[list[Any]] = []

    def run(self, query: str, chat_history: list[Any]) -> dict[str, Any]:
        self.histories.append(chat_history)
        return {"answer": f"Answer to {query}"}


def test_explicit_name_is_extracted_as_personal_information() -> None:
    assert extract_memory("I am Kanupriya") == (
        "User's name is Kanupriya",
        "personal_information",
    )


def test_preference_persists_across_conversations_and_is_user_scoped() -> None:
    user_id = "memory-user-a"
    other_user_id = "memory-user-b"
    clear_chat_history(user_id)
    clear_chat_history(other_user_id)

    service = ChatService()
    agent = FakeAgent()
    service._agent = agent  # type: ignore[assignment]

    service.ask(user_id, "I love Christopher Nolan movies.", "conversation-one")
    service.ask(user_id, "Recommend a movie for me.", "conversation-two")

    assert (
        get_user_memories(user_id)[0]["memory"] == "User likes Christopher Nolan movies"
    )
    assert get_user_memories(other_user_id) == []
    context = agent.histories[-1]
    assert isinstance(context[0], SystemMessage)
    assert "Christopher Nolan" in str(context[0].content)
    assert get_chat_history(user_id, "conversation-two") == [
        HumanMessage(content="Recommend a movie for me."),
        AIMessage(content="Answer to Recommend a movie for me."),
    ]


def test_name_is_retrieved_and_injected_in_a_new_conversation() -> None:
    user_id = "memory-user-name"
    clear_chat_history(user_id)

    service = ChatService()
    agent = FakeAgent()
    service._agent = agent  # type: ignore[assignment]

    service.ask(user_id, "I am Kanupriya", "conversation-one")
    service.ask(user_id, "What is my name?", "conversation-two")

    memories = get_user_memories(user_id)
    assert len(memories) == 1
    assert memories[0]["user_id"] == user_id
    assert memories[0]["memory"] == "User's name is Kanupriya"
    assert memories[0]["category"] == "personal_information"
    assert "User's name is Kanupriya" in str(agent.histories[-1][0].content)


def test_clear_history_keeps_long_term_memories() -> None:
    user_id = "memory-user-clear"
    clear_chat_history(user_id)

    service = ChatService()
    agent = FakeAgent()
    service._agent = agent  # type: ignore[assignment]
    service.ask(user_id, "I enjoy psychological thrillers.", "conversation")

    clear_chat_history(user_id)

    assert get_chat_history(user_id, "conversation") == []
    assert (
        get_user_memories(user_id)[0]["memory"] == "User likes psychological thrillers"
    )
