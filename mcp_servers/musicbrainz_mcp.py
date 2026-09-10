"""MusicBrainz MCP server for public music metadata and relationships."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from typing import Any

import requests
from mcp.server.fastmcp import FastMCP


logger = logging.getLogger(__name__)

MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2"
MUSICBRAINZ_USER_AGENT = "MediaMesh/0.1 (https://github.com/MediaMesh-poc)"
COVER_ART_ARCHIVE_URL = "https://coverartarchive.org/release"


class MusicBrainzAPIError(RuntimeError):
    """Raised when MusicBrainz cannot fulfill a request."""


@dataclass
class MusicBrainzClient:
    """Client for MusicBrainz's public JSON API."""

    session: requests.Session | None = None
    api_url: str = MUSICBRAINZ_API_URL
    user_agent: str = MUSICBRAINZ_USER_AGENT
    request_timeout: float = 20.0
    min_request_interval: float = 1.1

    def __post_init__(self) -> None:
        self.session = self.session or requests.Session()
        self._last_request_at = 0.0
        self._cover_art_cache: dict[str, str | None] = {}

    def _request(self, path: str, **params: Any) -> dict[str, Any]:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        params["fmt"] = "json"
        try:
            response = self.session.get(
                f"{self.api_url}{path}",
                params=params,
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                timeout=self.request_timeout,
            )
        except requests.RequestException as exc:
            raise MusicBrainzAPIError("MusicBrainz API request failed") from exc
        finally:
            self._last_request_at = time.monotonic()

        if response.status_code == 429:
            raise MusicBrainzAPIError("MusicBrainz rate limit reached; try again later")
        if response.status_code >= 400:
            raise MusicBrainzAPIError(
                _response_message(response, "MusicBrainz API request failed")
            )
        return _json_object(response, "MusicBrainz returned malformed data")

    def search_recordings(self, query: str) -> list[dict[str, Any]]:
        payload = self._request("/recording", query=query, limit=25)
        recordings = payload.get("recordings")
        if not isinstance(recordings, list) or not all(
            isinstance(recording, dict) for recording in recordings
        ):
            raise MusicBrainzAPIError(
                "MusicBrainz returned malformed recording results"
            )
        return [self._enrich_recording(recording) for recording in recordings]

    def get_recording(self, recording_id: str) -> dict[str, Any]:
        return self._enrich_recording(
            self._request(
                f"/recording/{recording_id}",
                inc="artists+releases+artist-rels+work-rels+recording-rels",
            )
        )

    def _enrich_recording(self, recording: dict[str, Any]) -> dict[str, Any]:
        normalized = _normalize_recording(recording)
        normalized["cover_url"] = self._get_cover_art(normalized["release_id"])
        return normalized

    def _get_cover_art(self, release_id: Any) -> str | None:
        if not isinstance(release_id, str) or not release_id.strip():
            return None
        if release_id in self._cover_art_cache:
            return self._cover_art_cache[release_id]

        cover_url = None
        try:
            response = self.session.get(
                f"{COVER_ART_ARCHIVE_URL}/{release_id}",
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                timeout=10,
            )
            if response.status_code < 400:
                payload = response.json()
                images = payload.get("images", []) if isinstance(payload, dict) else []
                for image in images if isinstance(images, list) else []:
                    if not isinstance(image, dict) or image.get("front") is not True:
                        continue
                    thumbnails = image.get("thumbnails", {})
                    if not isinstance(thumbnails, dict):
                        thumbnails = {}
                    cover_url = (
                        thumbnails.get("500")
                        or thumbnails.get("250")
                        or image.get("image")
                    )
                    break
        except (requests.RequestException, ValueError, TypeError) as exc:
            logger.info("Cover Art Archive lookup failed for %s: %s", release_id, exc)

        self._cover_art_cache[release_id] = cover_url
        return cover_url

    def search_artists(self, query: str) -> list[dict[str, Any]]:
        payload = self._request("/artist", query=query, limit=25)
        artists = payload.get("artists")
        if not isinstance(artists, list) or not all(
            isinstance(artist, dict) for artist in artists
        ):
            raise MusicBrainzAPIError("MusicBrainz returned malformed artist results")
        return [_normalize_artist(artist) for artist in artists]

    def get_artist(self, artist_id: str) -> dict[str, Any]:
        return _normalize_artist(
            self._request(f"/artist/{artist_id}", inc="aliases+artist-rels+url-rels")
        )


def _json_object(response: requests.Response, error_message: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise MusicBrainzAPIError(error_message) from exc
    if not isinstance(payload, dict):
        raise MusicBrainzAPIError(error_message)
    return payload


def _response_message(response: requests.Response, fallback: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        detail = getattr(response, "text", "").strip()
        return (
            f"{fallback} (HTTP {response.status_code}): {detail}"
            if detail
            else fallback
        )
    detail = payload.get("error") if isinstance(payload, dict) else None
    return f"{fallback} (HTTP {response.status_code}): {detail}" if detail else fallback


def _normalize_recording(recording: dict[str, Any]) -> dict[str, Any]:
    artist_credits = recording.get("artist-credit", [])
    artists = []
    for credit in artist_credits if isinstance(artist_credits, list) else []:
        artist = credit.get("artist") if isinstance(credit, dict) else None
        if isinstance(artist, dict):
            artists.append(
                {"artist_id": artist.get("id"), "artist_name": artist.get("name")}
            )
    releases = recording.get("releases", [])
    release_id = (
        next(
            (
                release.get("id")
                for release in releases
                if isinstance(release, dict) and release.get("id")
            ),
            None,
        )
        if isinstance(releases, list)
        else None
    )
    release_dates = [
        release.get("date-precision") or release.get("date")
        for release in releases
        if isinstance(release, dict) and release.get("date")
    ]
    return {
        "recording_id": recording.get("id"),
        "release_id": release_id,
        "title": recording.get("title"),
        "length_ms": recording.get("length"),
        "artists": artists,
        "release_dates": release_dates,
        "disambiguation": recording.get("disambiguation"),
        "relations": _normalize_relations(recording.get("relations", [])),
    }


def _normalize_artist(artist: dict[str, Any]) -> dict[str, Any]:
    return {
        "artist_id": artist.get("id"),
        "artist_name": artist.get("name"),
        "sort_name": artist.get("sort-name"),
        "country": artist.get("country"),
        "type": artist.get("type"),
        "disambiguation": artist.get("disambiguation"),
        "relations": _normalize_relations(artist.get("relations", [])),
    }


def _normalize_relations(relations: Any) -> list[dict[str, Any]]:
    if not isinstance(relations, list):
        return []
    normalized = []
    for relation in relations:
        if not isinstance(relation, dict):
            continue
        target = (
            relation.get("artist") or relation.get("recording") or relation.get("work")
        )
        if not isinstance(target, dict):
            continue
        normalized.append(
            {
                "type": relation.get("type"),
                "direction": relation.get("direction"),
                "target_id": target.get("id"),
                "target_name": target.get("name") or target.get("title"),
            }
        )
    return normalized


def _client_from_environment() -> MusicBrainzClient:
    return MusicBrainzClient()


def _tool_error(exc: MusicBrainzAPIError) -> dict[str, str]:
    logger.warning("MusicBrainz MCP tool failed: %s", exc)
    return {"error": str(exc)}


def _validate_id(value: str, label: str) -> str | None:
    if not value.strip():
        return f"MusicBrainz {label} ID cannot be empty"
    return None


mcp = FastMCP("MusicBrainz")


@mcp.tool()
def search_recordings(query: str) -> dict[str, Any]:
    """Search MusicBrainz recordings and return normalized metadata."""
    if not query.strip():
        return {"error": "Recording search query cannot be empty"}
    try:
        return {"recordings": _client_from_environment().search_recordings(query)}
    except MusicBrainzAPIError as exc:
        return _tool_error(exc)


@mcp.tool()
def get_recording(recording_id: str) -> dict[str, Any]:
    """Get recording metadata, artist credits, releases, and explicit relations."""
    validation_error = _validate_id(recording_id, "recording")
    if validation_error:
        return {"error": validation_error}
    try:
        return _client_from_environment().get_recording(recording_id)
    except MusicBrainzAPIError as exc:
        return _tool_error(exc)


@mcp.tool()
def search_artists(query: str) -> dict[str, Any]:
    """Search MusicBrainz artists and return normalized metadata."""
    if not query.strip():
        return {"error": "Artist search query cannot be empty"}
    try:
        return {"artists": _client_from_environment().search_artists(query)}
    except MusicBrainzAPIError as exc:
        return _tool_error(exc)


@mcp.tool()
def get_artist(artist_id: str) -> dict[str, Any]:
    """Get MusicBrainz artist metadata and explicit relations."""
    validation_error = _validate_id(artist_id, "artist")
    if validation_error:
        return {"error": validation_error}
    try:
        return _client_from_environment().get_artist(artist_id)
    except MusicBrainzAPIError as exc:
        return _tool_error(exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    mcp.run(transport="stdio")
