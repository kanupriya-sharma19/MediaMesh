from langchain_core.messages import AIMessage, HumanMessage

from backend.memory.chat_history import (
    clear_chat_history,
    get_chat_history,
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
