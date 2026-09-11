"""Pydantic contracts for the MediaMesh API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    confirm_password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    role: str
    content: Any


class ChatResponse(BaseModel):
    message: MessageResponse


class HistoryResponse(BaseModel):
    messages: list[MessageResponse]
