# SonicGraph

SonicGraph is a proof-of-concept real-time media intelligence agent. It calls live MusicBrainz and TMDB data through Model Context Protocol (MCP) tools, then uses an LLM to summarize only the evidence returned by those tools.

This repository contains a complete POC with MusicBrainz and TMDB as the active data sources. The agent calls MCP tools, then uses LangChain with Google Gemini to answer from the returned evidence.

## Architecture

```text
                    +--------------+
                    |   Streamlit  |
                    |      UI      |
                    +------+-------+
                           |
                           v
                    +--------------+
                    |    Agent     |
                    +------+-------+
                           |
                           v
                    +--------------+
                    |  MCP Client  |
                    +------+-------+
                           |
                +------------+------------+
                v                         v
         MusicBrainz MCP             TMDB MCP
                |                         |
                +------------+------------+
                               v
                       +--------------+
                       | Gemini LLM   |
                       +------+-------+
                               v
                       +--------------+
                       | Final Answer |
                       +--------------+
```

The LLM is instructed to use only structured MCP evidence and to say when a fact cannot be verified.

## Prerequisites

- Python 3.11 or newer
- A TMDB API key for movie data
- MusicBrainz does not require an API key

## Setup

From the repository root on Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
cp .env.example .env
```

Fill in `.env` with credentials. It is ignored by Git and must never be committed.

## Credentials

### TMDB

1. Create or sign in to a [TMDB account](https://www.themoviedb.org/).
2. Request an API key from account settings.
3. Put the key in `TMDB_API_KEY`.

The movie integration will use structured TMDB metadata and credits. A movie will not be treated as an A24 title based only on free-text descriptions.

## Running the TMDB MCP server

After filling in `TMDB_API_KEY` in `.env`, start the server with:

```powershell
.\.venv\Scripts\python.exe -m mcp_servers.tmdb_mcp
```

The server communicates over MCP stdio and exposes `search_movies`, `get_movie`, and `get_movie_credits`. Movie details preserve structured production companies, and credits preserve cast and crew fields for Gemini's grounded answers.

## Running the MusicBrainz MCP server

MusicBrainz is a public service and does not require an API key. It does require a descriptive `User-Agent`, which the SonicGraph server sends automatically, and public API requests are paced to respect MusicBrainz rate limits.

Start it with:

```powershell
.\.venv\Scripts\python.exe -m mcp_servers.musicbrainz_mcp
```

The server exposes `search_recordings`, `get_recording`, `search_artists`, and `get_artist`. Recording responses preserve MusicBrainz IDs, artist credits, release dates, and explicit MusicBrainz relationships. MusicBrainz metadata is not silently treated as producer credit unless the source explicitly identifies that relationship.

## Running the Streamlit app

With `.env` populated and the virtual environment active, run:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

The app starts the MusicBrainz and TMDB MCP servers through the Python MCP SDK over stdio, sends the retrieved evidence to LangChain's Gemini model, and displays the grounded answer and warnings. Set `GOOGLE_API_KEY` or `GEMINI_API_KEY` and optionally `GEMINI_MODEL` in `.env`.

## Current status

The active POC path uses MusicBrainz and TMDB MCP servers plus LangChain Gemini. Graph, Spotify, and unrelated entity-ingestion code have been removed from the active project. The private `.env` may still contain old ignored variables, but the runtime no longer reads or uses them.

Remaining phases: none for the POC scope.

## Future example queries

- Tell me about movie "Bahubali I".
- Find recent information about a film and its credits.
- Search MusicBrainz for an artist or recording.

## Limitations

- This is a POC, not a production architecture.
- Data freshness and API rate limits depend on the upstream services.
- LLM answers depend on the configured model and available API credentials.
- The project does not use LangGraph or evaluation frameworks at this stage.
