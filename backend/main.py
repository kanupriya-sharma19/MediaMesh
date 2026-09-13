"""FastAPI application for the MediaMesh React frontend."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api.auth import router as auth_router  # noqa: E402
from backend.api.chat import router as chat_router  # noqa: E402
from backend.api.landing import router as landing_router  # noqa: E402
from backend.services.dependencies import auth_service, chat_service  # noqa: E402


app = FastAPI(title="MediaMesh API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(landing_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
