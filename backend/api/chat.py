"""Protected chat and history endpoints."""

from __future__ import annotations

from typing import Annotated

from backend.agent.llm_agent import AgentError
from backend.agent.mcp_client import MCPClientError
from backend.api.auth import current_user
from backend.memory.chat_history import get_chat_sessions
from backend.schemas import ChatRequest, ChatResponse, HistoryResponse, SessionsResponse
from backend.services.chat_service import ChatService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.concurrency import run_in_threadpool


router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_chat_service() -> ChatService:
    from backend.services.dependencies import chat_service

    return chat_service


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    user: Annotated[dict[str, str], Depends(current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> dict[str, dict[str, object]]:
    try:
        result = await run_in_threadpool(
            service.ask, user["id"], payload.message.strip(), payload.session_id
        )
    except (AgentError, MCPClientError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return {"message": {"role": "assistant", "content": result}}


@router.get("/history", response_model=HistoryResponse)
async def history(
    user: Annotated[dict[str, str], Depends(current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
    session_id: str = Query(default="default", min_length=1, max_length=128),
) -> dict[str, list[dict[str, object]]]:
    return {
        "messages": await run_in_threadpool(service.history, user["id"], session_id)
    }


@router.get("/sessions", response_model=SessionsResponse)
async def sessions(
    user: Annotated[dict[str, str], Depends(current_user)],
) -> dict[str, list[dict[str, str]]]:
    return {"sessions": await run_in_threadpool(get_chat_sessions, user["id"])}


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(
    user: Annotated[dict[str, str], Depends(current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
    session_id: str = Query(default="default", min_length=1, max_length=128),
) -> None:
    await run_in_threadpool(service.clear, user["id"], session_id)
