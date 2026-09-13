# MediaMesh

<div align="center">
  <a href="https://www.youtube.com/watch?v=l4hnZI8Rsn8" target="_blank" rel="noopener noreferrer">
    <img src="https://img.youtube.com/vi/l4hnZI8Rsn8/maxresdefault.jpg" alt="MediaMesh demo video" width="960" />
  </a>
</div>

<p align="center">
  <strong>Project demo:</strong> <a href="https://www.youtube.com/watch?v=l4hnZI8Rsn8" target="_blank" rel="noopener noreferrer">Watch the MediaMesh demo on YouTube</a>
</p>

MediaMesh is an AI-powered media discovery app that connects movies, music, books, and related media through a grounded evidence workflow. The app combines a React frontend, a FastAPI backend, a custom LangChain + Gemini decision agent, and MCP-backed external media tools to answer cross-media questions with traceable evidence.

The product is designed for real-world media exploration: users can ask for recommendations, connections, similarities, and contextual comparisons, while the system keeps tool usage grounded in the actual external results it retrieved.

## What the project includes

- React + Vite frontend for the user-facing chat and auth experience
- FastAPI backend for authentication, chat APIs, sessions, and history
- Gemini-powered LangChain agent using Google Generative AI
- MCP tool orchestration for:
  - TMDB
  - MusicBrainz
  - Google Books
- Long-term memory and conversation memory for user preferences and context
- PostgreSQL/Supabase-backed persistence for authenticated chat and app data
- Streamlit UI for local testing and alternate access
- Safety guardrails for input, tools, and output validation
- Automated tests for agent behavior, MCP discovery, and safety checks

## Core features

- Ask one question across media types and get a single answer
- Search for movies, books, artists, recordings, and related media metadata
- Compare media by theme, relationship, similarity, and recommendation
- Ground responses in real tool results rather than unsupported invented facts
- Preserve user chat history and memory across sessions
- Keep the experience secure with guardrails for prompt injection and sensitive data

MediaMesh includes a production-appropriate safety layer around the current Gemini/LangChain architecture without replacing the model or rewriting the agent.

## Architecture

```text
React frontend
       |
       v
FastAPI backend
       |
       v
MediaMesh agent services
       |
       +--> Gemini LLM (Google Generative AI)
       +--> LangChain agent wrapper
       +--> MCP client
              |
              +--> TMDB MCP server
              +--> MusicBrainz MCP server
              +--> Google Books MCP server
```

The agent is designed to operate with minimal necessary tool usage and to return answers only when supported by actual tool evidence.

## Project structure

```text
MediaMesh/
├── backend/
│   ├── agent/              # Gemini agent, LLM adapter, MCP client
│   ├── api/                # FastAPI routes for auth and chat
│   ├── data/               # Local app data / migration inputs
│   ├── memory/             # Chat history and long-term memory
│   ├── mcp_servers/        # TMDB, MusicBrainz, and Google Books MCP servers
│   ├── services/           # Chat and auth service logic
│   ├── streamlit/          # Streamlit interface
│   ├── utils/              # Settings and config helpers
│   ├── __init__.py
│   ├── main.py             # FastAPI entry point
│   ├── README.md
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.js
│   └── README.md
├── alembic/
├── scripts/
├── tests/
│   ├── test_dynamic_agent.py
│   ├── test_guardrails.py
│   └── ...
├── .env.example
├── alembic.ini
├── package.json
├── README.md
└── UI_Image.png
```

## API endpoints

- `GET /api/health` - health check
- `GET /api/landing/media` - fetch media for marquee 
- `POST /api/auth/signup` - create an account
- `POST /api/auth/login` - start a session
- `POST /api/auth/logout` - end a session
- `GET /api/auth/me` - get the current user
- `POST /api/chat` - send a chat message
- `GET /api/chat/history` - retrieve chat history
- `DELETE /api/chat/history` - clear chat history
- `POST /api/chat/sessions` - create a session
- `GET /api/chat/sessions` - list sessions
- `GET /api/chat/sessions/{session_id}` - view one session

## Created & Maintained by

Kanupriya Sharma