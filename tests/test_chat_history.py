from langchain_core.messages import AIMessage, HumanMessage

from backend.memory.chat_history import (
    clear_chat_history,
    get_chat_history,
    get_chat_sessions,
    get_store,
    save_chat_history,
)


def test_user_can_save_and_retrieve_history() -> None:
    user_id = "history-user-a"
    clear_chat_history(user_id)
    messages = [
        HumanMessage(content="Recommend a sci-fi movie."),
        AIMessage(content="I recommend Arrival."),
    ]

    save_chat_history(user_id, messages)

    assert get_chat_history(user_id) == messages


def test_users_have_isolated_histories() -> None:
    user_a = "history-user-a-isolated"
    user_b = "history-user-b-isolated"
    clear_chat_history(user_a)
    clear_chat_history(user_b)
    save_chat_history(user_a, [HumanMessage(content="A's message")])

    assert get_chat_history(user_b) == []


def test_multiple_messages_preserve_order_and_roles() -> None:
    user_id = "history-user-order"
    clear_chat_history(user_id)
    messages = [
        HumanMessage(content="First"),
        AIMessage(content="Second"),
        HumanMessage(content="Third"),
    ]

    save_chat_history(user_id, messages)

    restored = get_chat_history(user_id)
    assert [(message.type, message.content) for message in restored] == [
        ("human", "First"),
        ("ai", "Second"),
        ("human", "Third"),
    ]


def test_clear_history_does_not_affect_another_user() -> None:
    user_a = "history-user-a-clear"
    user_b = "history-user-b-clear"
    clear_chat_history(user_a)
    clear_chat_history(user_b)
    save_chat_history(user_a, [HumanMessage(content="A's message")])
    save_chat_history(user_b, [HumanMessage(content="B's message")])

    clear_chat_history(user_a)

    assert get_chat_history(user_a) == []
    assert get_chat_history(user_b) == [HumanMessage(content="B's message")]


def test_clear_history_removes_all_user_sessions() -> None:
    user_id = "history-user-all-sessions"
    clear_chat_history(user_id)
    save_chat_history(user_id, [HumanMessage(content="First conversation")], "first")
    save_chat_history(user_id, [HumanMessage(content="Second conversation")], "second")

    clear_chat_history(user_id)

    assert get_chat_sessions(user_id) == []
    assert get_chat_history(user_id, "first") == []
    assert get_chat_history(user_id, "second") == []


def test_same_user_history_is_available_across_calls() -> None:
    user_id = "history-user-session"
    clear_chat_history(user_id)
    save_chat_history(user_id, [HumanMessage(content="Earlier conversation")])

    save_chat_history(
        user_id,
        get_chat_history(user_id) + [AIMessage(content="Earlier answer")],
    )

    assert [message.content for message in get_chat_history(user_id)] == [
        "Earlier conversation",
        "Earlier answer",
    ]


def test_store_is_singleton_for_application_lifetime() -> None:
    assert get_store() is get_store()


def test_sessions_store_title_and_sort_by_recent_activity() -> None:
    user_id = "history-user-metadata"
    clear_chat_history(user_id)
    save_chat_history(
        user_id,
        [
            HumanMessage(
                content="Can you recommend some books similar to The Martian?"
            ),
            AIMessage(content="Try Project Hail Mary."),
        ],
        "books-session",
    )
    save_chat_history(
        user_id,
        [HumanMessage(content="Find songs from recent A24 films")],
        "music-session",
    )

    sessions = get_chat_sessions(user_id)

    assert sessions[0]["id"] == "music-session"
    assert sessions[0]["title"] == "Find songs from recent A24 films"
    assert sessions[1]["title"] == "recommend some books similar to The..."
    assert {session["id"] for session in sessions} == {
        "books-session",
        "music-session",
    }


def test_sessions_are_isolated_by_user() -> None:
    user_a = "history-user-sessions-a"
    user_b = "history-user-sessions-b"
    clear_chat_history(user_a)
    clear_chat_history(user_b)
    save_chat_history(user_a, [HumanMessage(content="Private chat")], "private")

    assert get_chat_sessions(user_b) == []
