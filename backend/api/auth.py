"""Authentication endpoints."""

from __future__ import annotations

from typing import Annotated

from backend.schemas import LoginRequest, SignupRequest, UserResponse
from backend.services.auth_service import AuthError, AuthService
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status


router = APIRouter(prefix="/api/auth", tags=["auth"])
SESSION_COOKIE = "mm_session"


def get_auth_service() -> AuthService:
    from backend.services.dependencies import auth_service

    return auth_service


def current_user(
    service: Annotated[AuthService, Depends(get_auth_service)],
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict[str, str]:
    user = service.get_user_by_session(session)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    return user


@router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def signup(
    payload: SignupRequest,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict[str, str]:
    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Passwords do not match.",
        )
    try:
        user = service.create_user(payload.name, str(payload.email), payload.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    _set_session_cookie(response, service.create_session(user["id"]))
    return user


@router.post("/login", response_model=UserResponse)
def login(
    payload: LoginRequest,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> dict[str, str]:
    user = service.authenticate(str(payload.email), payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    _set_session_cookie(response, service.create_session(user["id"]))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> None:
    service.delete_session(session)
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax", path="/")


@router.get("/me", response_model=UserResponse)
def me(user: Annotated[dict[str, str], Depends(current_user)]) -> dict[str, str]:
    return user


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
