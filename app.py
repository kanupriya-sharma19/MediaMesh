"""Streamlit interface for the SonicGraph POC."""

from __future__ import annotations

import logging

import streamlit as st

from agent.mcp_client import MCPClientError, StdioMCPClient
from agent.llm_agent import AgentError, LLMAgent


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
st.set_page_config(page_title="SonicGraph", page_icon="🎧", layout="wide")


@st.cache_resource
def get_agent() -> LLMAgent:
    """Create one cached agent facade for the Streamlit session."""
    return LLMAgent(StdioMCPClient())


def _render_result(result: dict) -> None:
    st.subheader("Answer")
    st.write(result.get("answer", "No answer returned."))
    for warning in result.get("warnings", []):
        st.warning(warning)


st.title("🎧 SonicGraph")
st.caption("Real-Time Media Intelligence Agent")
st.write("Ask about verified relationships across music and film.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and isinstance(message["content"], dict):
            _render_result(message["content"])
        else:
            st.write(message["content"])

query = st.chat_input("Ask about a movie, song, artist, or film relationship")
if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Querying MCP sources and generating an answer..."):
                result = get_agent().run(query)
            _render_result(result)
            st.session_state.messages.append({"role": "assistant", "content": result})
        except (AgentError, MCPClientError) as exc:
            message = {
                "answer": f"I couldn't complete that query: {exc}",
                "warnings": [],
            }
            st.error(message["answer"])
            st.session_state.messages.append({"role": "assistant", "content": message})
