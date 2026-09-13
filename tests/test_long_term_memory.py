from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from backend.database import User, session_scope
from backend.memory.chat_history import clear_chat_history, get_chat_history
from backend.memory.user_memory import (
    extract_memory,
    extract_memories,
    get_user_memories,
)
from backend.services.chat_service import ChatService


def create_test_user() -> str:
    user_id = str(uuid4())
    with session_scope() as session:
        session.add(
            User(
                id=user_id,
                name="Memory Test User",
                email=f"{user_id}@example.test",
                password_hash="test-only",
            )
        )
    return user_id


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
    assert extract_memory(
        "hi my name is Taylor.can you tell me about Pride and Prejudice"
    ) == ("User's name is Taylor", "personal_information")
    assert extract_memories("my name is kp, i like comedy films") == [
        ("User's name is kp", "personal_information"),
        ("User likes comedy films", "preference"),
    ]


def test_preference_persists_across_conversations_and_is_user_scoped() -> None:
    user_id = create_test_user()
    other_user_id = create_test_user()
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
    user_id = create_test_user()
    clear_chat_history(user_id)

    service = ChatService()
    agent = FakeAgent()
    service._agent = agent  # type: ignore[assignment]

    service.ask(
        user_id,
        "my name is kp, i like comedy films",
        "conversation-one",
    )
    service.ask(user_id, "What is my name?", "conversation-two")

    memories = get_user_memories(user_id)
    assert {memory["memory"] for memory in memories} == {
        "User's name is kp",
        "User likes comedy films",
    }
    assert all(memory["user_id"] == user_id for memory in memories)
    assert "User's name is kp" in str(agent.histories[-1][0].content)

    service.ask(user_id, "What do I like?", "conversation-three")
    assert "User likes comedy films" in str(agent.histories[-1][0].content)


def test_clear_history_keeps_long_term_memories() -> None:
    user_id = create_test_user()
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
