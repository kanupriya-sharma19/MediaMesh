"""Synchronous facade for calling SonicGraph MCP servers over stdio."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, ClassVar

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClientError(RuntimeError):
    """Raised when an MCP server cannot be started or returns invalid data."""


class StdioMCPClient:
    """Call local MusicBrainz and TMDB MCP servers through the MCP SDK."""

    _SERVER_MODULES: ClassVar[dict[str, str]] = {
        "TMDB": "mcp_servers.tmdb_mcp",
        "MusicBrainz": "mcp_servers.musicbrainz_mcp",
    }

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[1]

    def call(self, server: str, tool: str, **arguments: Any) -> dict[str, Any]:
        """Start one local MCP server, call one tool, and return its JSON object."""
        module = self._SERVER_MODULES.get(server)
        if module is None:
            raise MCPClientError(f"Unknown MCP server: {server}")
        try:
            return asyncio.run(self._call(module, tool, arguments))
        except MCPClientError:
            raise
        except Exception as exc:
            raise MCPClientError(f"MCP call {server}.{tool} failed") from exc

    async def _call(
        self, module: str, tool: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", module],
            env=os.environ.copy(),
            cwd=str(self.project_root),
        )
        async with (
            stdio_client(parameters) as (
                read_stream,
                write_stream,
            ),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()
            result = await session.call_tool(tool, arguments=arguments)
        if getattr(result, "isError", False) or getattr(result, "is_error", False):
            raise MCPClientError(f"MCP tool {tool} returned an error")
        return _decode_result(result)


def _decode_result(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structuredContent", None)
    if structured is None:
        structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        return structured

    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if not isinstance(text, str):
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise MCPClientError("MCP tool returned no JSON object")
