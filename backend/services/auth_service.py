"""PostgreSQL-backed users and server-side browser sessions."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from backend.database import AuthSession, User, session_scope
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


class AuthError(ValueError):
    """Raised when an authentication operation cannot be completed."""


class AuthService:
    def create_user(self, name: str, email: str, password: str) -> dict[str, str]:
        user_id = str(uuid.uuid4())
        normalized_email = email.strip().lower()
        with session_scope() as session:
            session.add(
                User(
                    id=user_id,
                    name=name.strip(),
                    email=normalized_email,
                    password_hash=_hash_password(password),
                )
            )
            try:
                session.flush()
            except IntegrityError as exc:
                raise AuthError("An account with that email already exists.") from exc
        return {"id": user_id, "name": name.strip(), "email": normalized_email}

    def authenticate(self, email: str, password: str) -> dict[str, str] | None:
        with session_scope() as session:
            user = session.scalar(
                select(User).where(User.email == email.strip().lower())
            )
            if user is None or not _verify_password(password, user.password_hash):
                return None
            return {"id": user.id, "name": user.name, "email": user.email}

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        with session_scope() as session:
            session.add(
                AuthSession(
                    token_hash=_token_hash(token),
                    user_id=user_id,
                    expires_at=datetime.now(UTC) + timedelta(days=7),
                )
            )
        return token

    def get_user_by_session(self, token: str | None) -> dict[str, str] | None:
        if not token:
            return None
        with session_scope() as session:
            auth_session = session.scalar(
                select(AuthSession).where(AuthSession.token_hash == _token_hash(token))
            )
            if auth_session is None:
                return None
            if auth_session.expires_at <= datetime.now(UTC):
                session.delete(auth_session)
                return None
            user = session.get(User, auth_session.user_id)
            return (
                {"id": user.id, "name": user.name, "email": user.email}
                if user
                else None
            )

    def delete_session(self, token: str | None) -> None:
        if not token:
            return
        with session_scope() as session:
            auth_session = session.get(AuthSession, _token_hash(token))
            if auth_session:
                session.delete(auth_session)


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii")
    return f"scrypt${encode(salt)}${encode(digest)}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_value, digest_value = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_value.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_value.encode("ascii"))
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
