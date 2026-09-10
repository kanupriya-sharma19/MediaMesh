"""Streamlit interface for the MediaMesh application."""

from __future__ import annotations

import logging
import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from agent.llm_agent import AgentError, LLMAgent
from agent.mcp_client import MCPClientError, StdioMCPClient
from memory.chat_history import clear_chat_history, get_chat_history, save_chat_history
from ui.components import (
    render_chat_message,
    render_empty_state,
    render_header,
    render_sidebar,
)
from ui.theme import inject_custom_css


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
st.set_page_config(
    page_title="MediaMesh · Cross-media discovery", page_icon="✦", layout="wide"
)


@st.cache_resource
def get_agent() -> LLMAgent:
    """Create one cached agent facade for the Streamlit session."""
    return LLMAgent(StdioMCPClient())


def _clear_current_history() -> None:
    clear_chat_history(st.session_state.user_id)
    st.session_state.messages = []
    st.rerun()


def _run_query(query: str) -> None:
    st.session_state.messages.append({"role": "user", "content": query})
    try:
        with st.status("✦ Exploring the media graph...", expanded=False) as status:
            history = get_chat_history(st.session_state.user_id)
            history.append(HumanMessage(content=query))
            result = get_agent().run(query, chat_history=history)
            status.update(label="Discovery complete", state="complete")
        history.append(AIMessage(content=result.get("answer", "")))
        save_chat_history(st.session_state.user_id, history)
        st.session_state.messages.append({"role": "assistant", "content": result})
    except (AgentError, MCPClientError) as exc:
        result = {
            "answer": "MediaMesh couldn't complete that search right now.",
            "warnings": [str(exc)],
        }
        history = get_chat_history(st.session_state.user_id)
        history.extend(
            [HumanMessage(content=query), AIMessage(content=result["answer"])]
        )
        save_chat_history(st.session_state.user_id, history)
        st.session_state.messages.append({"role": "assistant", "content": result})


if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "user" if isinstance(message, HumanMessage) else "assistant",
            "content": message.content,
        }
        for message in get_chat_history(st.session_state.user_id)
    ]

inject_custom_css()
render_sidebar(st.session_state.messages, _clear_current_history)
render_header()

if not st.session_state.messages:
    suggested_query = render_empty_state()
    if suggested_query:
        st.session_state.pending_query = suggested_query

for message in st.session_state.messages:
    render_chat_message(message)

typed_query = st.chat_input(
    "Ask about movies, music, books, or unexpected connections..."
)
query = typed_query or st.session_state.pop("pending_query", None)
if query:
    _run_query(query)
    st.rerun()
