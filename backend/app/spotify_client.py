import time

import httpx

from app.config import Settings

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"

# Refresh a little before actual expiry to avoid racing a request against the deadline.
_EXPIRY_SAFETY_MARGIN_SECONDS = 30


class SpotifyApiError(Exception):
    """Base class for errors surfaced from the Spotify Web API."""


class SpotifyNotFoundError(SpotifyApiError):
    pass


class SpotifyRateLimitedError(SpotifyApiError):
    def __init__(self, retry_after_seconds: int | None = None):
        super().__init__("Spotify rate limit exceeded.")
        self.retry_after_seconds = retry_after_seconds


class SpotifyAuthError(SpotifyApiError):
    pass


class SpotifyClient:
    """Thin async client for the Spotify Web API, authenticated via the
    Client Credentials flow (app-level access, no user login involved).
    """

    def __init__(self, settings: Settings, http_client: httpx.AsyncClient | None = None):
        self._settings = settings
        self._http = http_client or httpx.AsyncClient(timeout=10.0)
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _get_access_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token

        response = await self._http.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self._settings.spotify_client_id, self._settings.spotify_client_secret),
        )
        if response.status_code != 200:
            raise SpotifyAuthError(
                f"Failed to obtain Spotify access token (status {response.status_code})."
            )

        payload = response.json()
        self._token = payload["access_token"]
        expires_in = payload.get("expires_in", 3600)
        self._token_expires_at = time.monotonic() + expires_in - _EXPIRY_SAFETY_MARGIN_SECONDS
        return self._token

    async def _get(self, path: str) -> dict:
        token = await self._get_access_token()
        response = await self._http.get(
            f"{API_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code == 404:
            raise SpotifyNotFoundError(f"Spotify resource not found: {path}")
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise SpotifyRateLimitedError(int(retry_after) if retry_after else None)
        response.raise_for_status()
        return response.json()

    async def get_album(self, album_id: str) -> dict:
        return await self._get(f"/albums/{album_id}")

    async def get_album_tracks(self, album_id: str, limit: int = 50) -> dict:
        return await self._get(f"/albums/{album_id}/tracks?limit={limit}")

    async def get_playlist(self, playlist_id: str) -> dict:
        return await self._get(f"/playlists/{playlist_id}")

    async def get_playlist_items(self, playlist_id: str, limit: int = 100) -> dict:
        return await self._get(f"/playlists/{playlist_id}/items?limit={limit}")
