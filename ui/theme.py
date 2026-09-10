"""Visual theme for the MediaMesh Streamlit application."""

from __future__ import annotations

import streamlit as st


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
  --mm-bg: #08060d;
  --mm-panel: rgba(24, 17, 35, .82);
  --mm-panel-soft: rgba(30, 21, 45, .62);
  --mm-border: rgba(226, 190, 255, .14);
  --mm-text: #f9f5ff;
  --mm-muted: #a79bb6;
  --mm-purple: #a855f7;
  --mm-pink: #f472b6;
  --mm-cyan: #67e8f9;
}

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp {
  color: var(--mm-text);
  background: radial-gradient(circle at 84% 2%, rgba(168,85,247,.17), transparent 28rem),
              radial-gradient(circle at 8% 42%, rgba(244,114,182,.08), transparent 24rem),
              linear-gradient(135deg, #08060d 0%, #100a19 52%, #08060d 100%);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stDecoration"] { display: none; }
.block-container { max-width: 1280px; padding: 2.25rem 4rem 4rem; }
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, rgba(18, 11, 29, .98), rgba(10, 7, 16, .98));
  border-right: 1px solid var(--mm-border);
}

section[data-testid="stSidebar"] > div {
  padding: 1.0rem 1.15rem;
}

section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
  padding-top: 0.11rem;
}
.mm-brand { font-family: 'Space Grotesk', sans-serif; letter-spacing: .2em; font-weight: 700; }
.mm-kicker { color: var(--mm-pink); font-size: .72rem; font-weight: 700; letter-spacing: .18em; text-transform: uppercase; }
.mm-hero { padding: 1.2rem 0 2.2rem; }
.mm-hero h1 { font-family: 'Space Grotesk', sans-serif; font-size: clamp(2.5rem, 6vw, 5.8rem); letter-spacing: -.05em; line-height: .98; margin: .45rem 0 1rem; }
.mm-gradient { background: linear-gradient(110deg, #fff 12%, #f0abfc 52%, #f472b6 92%); -webkit-background-clip: text; background-clip: text; color: transparent; }
.mm-subtitle { color: var(--mm-muted); font-size: 1.08rem; max-width: 40rem; line-height: 1.6; }
.mm-section-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.1rem; letter-spacing: -.01em; margin: 1.4rem 0 .8rem; }
.mm-panel, .mm-card { background: var(--mm-panel); border: 1px solid var(--mm-border); border-radius: 18px; box-shadow: 0 18px 50px rgba(0,0,0,.2); }
.mm-panel { padding: 1.15rem; }
.mm-card { overflow: hidden;  margin-bottom: 32px; height: 100%; transition: border-color .2s ease, transform .2s ease, box-shadow .2s ease; }
.mm-card:hover { border-color: rgba(244,114,182,.5); box-shadow: 0 10px 32px rgba(168,85,247,.16); transform: translateY(-2px); }
.mm-card img { width: 100%; aspect-ratio: 2 / 3; object-fit: cover; display: block; }
.mm-card img.mm-card-music-image, .mm-card-music-art { aspect-ratio: 1; }
.mm-card-art { aspect-ratio: 2 / 3; display: grid; place-items: center; color: var(--mm-muted); background: linear-gradient(145deg, #261735, #0f0b18); font-size: 2rem; }
.mm-card-body { padding: .9rem 1rem 1.1rem; }
.mm-card-title { color: var(--mm-text); font-family: 'Space Grotesk', sans-serif; font-size: 1rem; font-weight: 600; margin-bottom: .3rem; }
.mm-card-meta, .mm-card-detail { color: var(--mm-muted); font-size: .83rem; line-height: 1.45; }
.mm-tag { display: inline-block; color: #f3d8ff; background: rgba(168,85,247,.16); border: 1px solid rgba(168,85,247,.28); border-radius: 999px; font-size: .7rem; letter-spacing: .08em; padding: .25rem .55rem; text-transform: uppercase; }
.mm-message { border: 1px solid var(--mm-border); border-radius: 18px; padding: 1rem 1.1rem; margin: .6rem 0; background: rgba(22, 15, 33, .76); }
.mm-message.user { margin-left: 12%; background: linear-gradient(135deg, rgba(99,40,130,.7), rgba(57,27,77,.82)); border-color: rgba(217, 136, 255, .22); }
.mm-message-head { color: var(--mm-pink); font-size: .68rem; font-weight: 700; letter-spacing: .16em; margin-bottom: .55rem; text-transform: uppercase; }
.mm-answer { color: #eee8f4; line-height: 1.7; white-space: pre-wrap; }
.mm-connection { align-items: center; background: var(--mm-panel-soft); border: 1px solid var(--mm-border); border-radius: 14px; display: flex; gap: .75rem; padding: .8rem 1rem; }
.mm-connection + .mm-connection { margin-top: .55rem; }
.mm-arrow { color: var(--mm-pink); font-size: 1.3rem; }
.mm-source { color: var(--mm-muted); font-size: .78rem; }
[data-testid="stChatInput"] { border-color: rgba(244,114,182,.38); border-radius: 20px; background: rgba(27, 17, 38, .92); box-shadow: 0 0 28px rgba(168,85,247,.11); }
[data-testid="stChatInput"] textarea { color: var(--mm-text); }
.stButton > button { border: 1px solid var(--mm-border); border-radius: 12px; color: var(--mm-text); background: rgba(39, 25, 52, .68); transition: all .2s ease; }
.stButton > button:hover { border-color: var(--mm-pink); color: #fff; background: rgba(114, 48, 135, .55); }
.mm-quick { color: #d7cce0; font-size: .86rem; line-height: 1.35; }
.mm-sidebar-label { color: #7f718f; font-size: .68rem; font-weight: 700; letter-spacing: .16em; margin: 1.25rem 0 .55rem; text-transform: uppercase; }
.mm-status {
  color: #b9aeca;
  font-size: 1rem;
  padding: .22rem 0;
}
.mm-status span { color: #86efac; margin-right: .4rem; }
@media (max-width: 800px) { .block-container { padding: 1.4rem 1rem 3rem; } .mm-message.user { margin-left: 0; } .mm-hero h1 { font-size: 3.2rem; } }
</style>
"""


def inject_custom_css() -> None:
    """Inject the app-wide MediaMesh theme."""
    st.markdown(CSS, unsafe_allow_html=True)
