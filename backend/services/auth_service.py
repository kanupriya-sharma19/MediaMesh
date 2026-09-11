"""SQLite-backed users and server-side browser sessions."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path


class AuthError(ValueError):
    """Raised when an authentication operation cannot be completed."""


class AuthService:
    def __init__(self, database_path: Path | None = None) -> None:
        default_path = Path(__file__).resolve().parents[1] / "data" / "mm.db"
        self.database_path = database_path or Path(
            os.getenv("MEDIAMESH_DB_PATH", str(default_path))
        )
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS sessions_user_id_idx ON sessions(user_id);
                """
            )

    def create_user(self, name: str, email: str, password: str) -> dict[str, str]:
        user_id = str(uuid.uuid4())
        normalized_email = email.strip().lower()
        with self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO users (id, name, email, password_hash) VALUES (?, ?, ?, ?)",
                    (user_id, name.strip(), normalized_email, _hash_password(password)),
                )
            except sqlite3.IntegrityError as exc:
                raise AuthError("An account with that email already exists.") from exc
        return {"id": user_id, "name": name.strip(), "email": normalized_email}

    def authenticate(self, email: str, password: str) -> dict[str, str] | None:
        with self._connect() as connection:
            user = connection.execute(
                "SELECT id, name, email, password_hash FROM users WHERE email = ?",
                (email.strip().lower(),),
            ).fetchone()
        if user is None or not _verify_password(password, user["password_hash"]):
            return None
        return {"id": user["id"], "name": user["name"], "email": user["email"]}

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(days=7)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (_token_hash(token), user_id, expires_at.isoformat()),
            )
        return token

    def get_user_by_session(self, token: str | None) -> dict[str, str] | None:
        if not token:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT users.id, users.name, users.email, sessions.expires_at
                FROM sessions JOIN users ON users.id = sessions.user_id
                WHERE sessions.token_hash = ?
                """,
                (_token_hash(token),),
            ).fetchone()
        if row is None:
            return None
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at <= datetime.now(UTC):
            self.delete_session(token)
            return None
        return {"id": row["id"], "name": row["name"], "email": row["email"]}

    def delete_session(self, token: str | None) -> None:
        if token:
            with self._connect() as connection:
                connection.execute(
                    "DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),)
                )


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
