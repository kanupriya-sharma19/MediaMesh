"""Protected chat and history endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from backend.api.auth import current_user
from backend.schemas import ChatRequest, ChatResponse, HistoryResponse, MessageResponse
from backend.services.chat_service import ChatService
from backend.agent.llm_agent import AgentError
from backend.agent.mcp_client import MCPClientError


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
            service.ask, user["id"], payload.message.strip()
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
) -> dict[str, list[dict[str, object]]]:
    return {"messages": await run_in_threadpool(service.history, user["id"])}


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def clear_history(
    user: Annotated[dict[str, str], Depends(current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> None:
    await run_in_threadpool(service.clear, user["id"])
