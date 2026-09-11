import asyncio
from types import SimpleNamespace
from typing import Any

from backend.agent.mcp_client import StdioMCPClient


def test_async_tool_discovery_maps_mcp_tool_fields(monkeypatch: Any) -> None:
    client = StdioMCPClient()
    tool = SimpleNamespace(
        name="search_books",
        description=None,
        inputSchema={"type": "object", "properties": {}},
    )
    result = SimpleNamespace(tools=[tool])

    class FakeSession:
        def __init__(self, read_stream: object, write_stream: object) -> None:
            pass

        async def __aenter__(self) -> "FakeSession":
            return self

        async def __aexit__(self, *args: Any) -> None:
            return None

        async def initialize(self) -> None:
            return None

        async def list_tools(self) -> Any:
            return result

    class FakeStdio:
        async def __aenter__(self) -> tuple[object, object]:
            return object(), object()

        async def __aexit__(self, *args: Any) -> None:
            return None

    monkeypatch.setattr("backend.agent.mcp_client.ClientSession", FakeSession)
    monkeypatch.setattr(
        "backend.agent.mcp_client.stdio_client", lambda parameters: FakeStdio()
    )

    tools = asyncio.run(client._list_tools("module", "GoogleBooks"))

    assert tools == [
        {
            "server": "GoogleBooks",
            "name": "search_books",
            "description": "",
            "input_schema": {"type": "object", "properties": {}},
        }
    ]
