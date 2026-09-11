"""Protected chat and history endpoints."""

from __future__ import annotations

from typing import Annotated

from backend.agent.llm_agent import AgentError
from backend.agent.mcp_client import MCPClientError
from backend.api.auth import current_user
from backend.schemas import (
    ChatRequest,
    ChatResponse,
    HistoryResponse,
    SessionResponse,
    SessionsResponse,
)
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


@router.post(
    "/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED
)
async def create_session(
    user: Annotated[dict[str, str], Depends(current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> dict[str, str]:
    return await run_in_threadpool(service.create_session, user["id"])


@router.get("/sessions", response_model=SessionsResponse)
async def sessions(
    user: Annotated[dict[str, str], Depends(current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> dict[str, list[dict[str, str]]]:
    return {"sessions": await run_in_threadpool(service.sessions, user["id"])}


@router.get("/sessions/{session_id}", response_model=HistoryResponse)
async def session_history(
    session_id: str,
    user: Annotated[dict[str, str], Depends(current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> dict[str, list[dict[str, object]]]:
    return {
        "messages": await run_in_threadpool(service.history, user["id"], session_id)
    }


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(
    user: Annotated[dict[str, str], Depends(current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> None:
    await run_in_threadpool(service.clear, user["id"])
