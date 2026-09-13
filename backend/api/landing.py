"""Public landing page data endpoints."""

from fastapi import APIRouter

from backend.services.landing_media import get_landing_media


router = APIRouter(prefix="/api/landing", tags=["landing"])


@router.get("/media")
def landing_media() -> dict[str, list[dict[str, str]]]:
    return get_landing_media()
