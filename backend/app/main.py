from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.config import Settings, get_settings
from app.database import get_session, init_db
from app.lookup import build_lookup_result
from app.models import LookupLog
from app.schemas import LookupResult
from app.spotify_client import (
    SpotifyApiError,
    SpotifyAuthError,
    SpotifyClient,
    SpotifyNotFoundError,
    SpotifyRateLimitedError,
)
from app.url_parsing import InvalidSpotifyUrlError, parse_spotify_reference


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Album Flow API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def get_spotify_client(settings: Settings = Depends(get_settings)) -> SpotifyClient:
    return SpotifyClient(settings)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/lookup", response_model=LookupResult)
async def lookup(
    url: str = Query(..., description="A Spotify album or playlist URL or URI"),
    session: Session = Depends(get_session),
) -> LookupResult:
    ref = parse_spotify_reference(url)

    settings = get_settings()
    client = SpotifyClient(settings)
    try:
        result = await build_lookup_result(client, ref)
    finally:
        await client.aclose()

    session.add(
        LookupLog(item_type=result.item_type, spotify_id=result.spotify_id, name=result.name)
    )
    session.commit()

    return result


@app.exception_handler(InvalidSpotifyUrlError)
async def invalid_url_handler(request, exc: InvalidSpotifyUrlError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(SpotifyNotFoundError)
async def not_found_handler(request, exc: SpotifyNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": "That album or playlist could not be found on Spotify."},
    )


@app.exception_handler(SpotifyRateLimitedError)
async def rate_limited_handler(request, exc: SpotifyRateLimitedError):
    headers = {"Retry-After": str(exc.retry_after_seconds)} if exc.retry_after_seconds else {}
    return JSONResponse(
        status_code=429,
        content={"detail": "Spotify rate limit exceeded. Please try again shortly."},
        headers=headers,
    )


@app.exception_handler(SpotifyAuthError)
async def auth_error_handler(request, exc: SpotifyAuthError):
    return JSONResponse(
        status_code=502,
        content={"detail": "Could not authenticate with Spotify. Check server configuration."},
    )


@app.exception_handler(SpotifyApiError)
async def generic_spotify_error_handler(request, exc: SpotifyApiError):
    return JSONResponse(
        status_code=502,
        content={"detail": "Spotify returned an unexpected error. Please try again."},
    )
