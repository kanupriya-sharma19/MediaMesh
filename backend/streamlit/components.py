"""Reusable, data-driven Streamlit components for MediaMesh."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st


QUICK_PROMPTS = (
    "Find an artist connected to this movie",
    "Recommend a book based on my movies",
    "Find songs from recent A24 films",
    "Discover unexpected media connections",
)


def render_sidebar(
    messages: list[dict[str, Any]], on_clear: Callable[[], None]
) -> str | None:
    with st.sidebar:
        st.markdown('<div class="mm-brand">MEDIAMESH</div>', unsafe_allow_html=True)
        st.caption("Cross-media intelligence")
        st.markdown(
            '<div class="mm-sidebar-label">Explore</div>', unsafe_allow_html=True
        )
        for icon, label in (
            ("⌂", "Discover"),
            ("✦", "Chat"),
            ("↗", "Connections"),
            ("◷", "History"),
        ):
            st.markdown(
                f'<div class="mm-status"><span>{icon}</span>{label}</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div class="mm-sidebar-label">Media sources</div>', unsafe_allow_html=True
        )
        for icon, label in (("●", "MusicBrainz"), ("●", "TMDB"), ("●", "Google Books")):
            st.markdown(
                f'<div class="mm-status"><span>{icon}</span>{label}</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div class="mm-sidebar-label">Recent chats</div>', unsafe_allow_html=True
        )
        titles = [
            message["content"] for message in messages if message.get("role") == "user"
        ]
        if titles:
            for title in titles[-4:][::-1]:
                st.markdown(
                    f'<div class="mm-status">• {_shorten(str(title), 34)}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Your discoveries will appear here.")

        if st.button("Clear history", use_container_width=True):
            on_clear()
        st.markdown(
        '<div style="text-align: center; color: #7f718f; font-size: .75rem; margin-top: 0.3rem;">Private session</div>',
        unsafe_allow_html=True,
    )
        return None


def render_header() -> None:
    st.markdown(
        '<div class="mm-hero"><div class="mm-kicker">Your media, connected</div>'
        '<h1><span class="mm-gradient">Discover what links</span><br>the things you love.</h1>'
        '<div class="mm-subtitle">Ask one question across music, movies and books. MediaMesh finds the signal between them.</div></div>',
        unsafe_allow_html=True,
    )


def render_quick_prompts() -> str | None:
    st.markdown(
        '<div class="mm-section-title">Start with a direction</div>',
        unsafe_allow_html=True,
    )
    columns = st.columns(4)
    for column, prompt in zip(columns, QUICK_PROMPTS):
        with column:
            if st.button(prompt, key=f"quick_{prompt}", use_container_width=True):
                return prompt
    return None


def render_empty_state() -> str | None:
    st.markdown(
        '<div class="mm-panel"><div class="mm-kicker">A new thread</div>'
        '<div class="mm-section-title">Find the connections hiding between the things you love.</div>'
        '<div class="mm-card-detail">Try a prompt below, or ask MediaMesh anything at the bottom of the page.</div></div>',
        unsafe_allow_html=True,
    )
    return render_quick_prompts()


def render_chat_message(message: dict[str, Any]) -> None:
    role = message.get("role", "assistant")
    content = message.get("content", "")
    if role == "user":
        st.markdown(
            f'<div class="mm-message user"><div class="mm-message-head">You</div>'
            f'<div class="mm-answer">{_escape(str(content))}</div></div>',
            unsafe_allow_html=True,
        )
        return

    result = content if isinstance(content, dict) else {"answer": str(content)}
    st.markdown(
        '<div class="mm-message"><div class="mm-message-head">✦ MediaMesh</div>'
        f'<div class="mm-answer">{_escape(str(result.get("answer", "No answer returned.")))}</div></div>',
        unsafe_allow_html=True,
    )
    render_warnings(result.get("warnings", []))
    render_media_results(result.get("sources", []))


def render_warnings(warnings: Any) -> None:
    if isinstance(warnings, list):
        for warning in warnings:
            st.warning(str(warning))


def render_media_results(sources: Any) -> None:
    if not isinstance(sources, list):
        return
    records: list[tuple[str, dict[str, Any]]] = []
    connections: list[tuple[str, str, str]] = []
    for source in sources:
        if not isinstance(source, dict) or source.get("type") != "tool_result":
            continue
        server = str(source.get("server", ""))
        result = source.get("result")
        if not isinstance(result, dict):
            continue
        for key, kind in (
            ("movies", "movie"),
            ("books", "book"),
            ("recordings", "music"),
            ("artists", "artist"),
        ):
            values = result.get(key)
            if isinstance(values, list):
                records.extend(
                    (kind, value) for value in values[:6] if isinstance(value, dict)
                )
        for key, kind in (
            ("movies", "movie"),
            ("books", "book"),
            ("recordings", "music"),
            ("artists", "artist"),
        ):
            values = result.get(key)
            if isinstance(values, list) and values:
                connections.append(
                    (
                        server,
                        kind,
                        str(
                            values[0].get("title")
                            or values[0].get("name")
                            or values[0].get("artist_name")
                            or "Result"
                        ),
                    )
                )

    if records:
        st.markdown(
            '<div class="mm-section-title">Similar Media</div>', unsafe_allow_html=True
        )
        columns = st.columns(min(4, len(records)))
        for column, (kind, record) in zip(
            columns * ((len(records) + len(columns) - 1) // len(columns)), records
        ):
            with column:
                render_media_card(kind, record)
    if len(connections) > 1:
        st.markdown(
            '<div class="mm-section-title">The thread between them</div>',
            unsafe_allow_html=True,
        )
        for index, (_, kind, title) in enumerate(connections):
            arrow = "→" if index < len(connections) - 1 else ""
            next_title = (
                connections[index + 1][2] if index < len(connections) - 1 else ""
            )
            label = f"{title} {arrow} {next_title}" if next_title else title
            st.markdown(
                f'<div class="mm-connection"><span class="mm-tag">{kind}</span><span>{_escape(label)}</span><span class="mm-arrow">{arrow}</span></div>',
                unsafe_allow_html=True,
            )


def render_media_card(kind: str, item: dict[str, Any]) -> None:
    title = (
        item.get("title") or item.get("name") or item.get("artist_name") or "Untitled"
    )
    if kind == "movie":
        meta = item.get("release_date") or "Movie"
        detail = item.get("overview") or "TMDB result"
        image = item.get("poster_url")
        icon = "🎬"
    elif kind == "book":
        authors = item.get("authors") or []
        meta = ", ".join(str(author) for author in authors[:2]) or "Google Books"
        detail = (item.get("categories") or ["Book"])[0]
        image = item.get("thumbnail")
        icon = "📚"
    elif kind == "music":
        artists = item.get("artists") or []
        meta = (
            ", ".join(
                str(artist.get("artist_name"))
                for artist in artists[:2]
                if isinstance(artist, dict)
            )
            or "MusicBrainz"
        )
        detail = item.get("release_dates") or "Recording"
        image = item.get("cover_url")
        icon = "🎵"
    else:
        meta = item.get("country") or item.get("type") or "Artist"
        detail = item.get("disambiguation") or "MusicBrainz result"
        image = None
        icon = "🎵"
    image_class = " mm-card-music-image" if kind == "music" else ""
    placeholder_class = " mm-card-music-art" if kind == "music" else ""
    artwork = (
        f'<img class="{image_class.strip()}" src="{_escape(str(image))}" alt="" />'
        if image
        else f'<div class="mm-card-art{placeholder_class}">{icon}</div>'
    )
    st.markdown(
        f'<div class="mm-card">{artwork}<div class="mm-card-body"><div class="mm-card-title">{_escape(str(title))}</div>'
        f'<div class="mm-card-meta">{_escape(str(meta))}</div><div class="mm-card-detail">{_escape(str(detail))[:110]}</div></div></div>',
        unsafe_allow_html=True,
    )


def _shorten(value: str, length: int) -> str:
    return value if len(value) <= length else value[: length - 1].rstrip() + "…"


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
