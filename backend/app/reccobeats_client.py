"""Primary per-track vibe source: ReccoBeats' free audio-features API.

ReccoBeats (https://reccobeats.com) republishes Spotify-audio-features-shaped
values (energy, valence, danceability, tempo, etc.) computed by its own
pipeline, keyed by track identity rather than by needing a 30-second preview
clip to analyze. This is the primary vibe source; app/vibe_analysis.py's
preview+librosa path is now the fallback for whenever ReccoBeats has no match
(see app/vibe_service.py and the project AGENTS.md for why - preview-URL
availability turned out to be far rarer in practice than originally assumed).

The contract below was confirmed against ReccoBeats' own OpenAPI spec (the
JSON embedded in its docs site's page bundles, not just the rendered HTML,
which loads request/response details client-side and doesn't expose them to
a plain fetch):

  - Base URL: https://api.reccobeats.com - no API key or Authorization header
    is required for any endpoint used here (confirmed via ReccoBeats' own
    "Introduction" doc page: "No API access key or authentication
    required"). There is therefore no RECCOBEATS_API_KEY setting to add.
  - `GET /v1/track?ids=<id>` resolves one or more tracks by ReccoBeats ID,
    Spotify ID, *or* ISRC, returning each match's own ReccoBeats UUID. This
    module passes the Spotify track ID already in hand (from the Spotify
    lookup - see app/lookup.py) rather than searching by track name + artist
    via `GET /v1/track/search`: an ID match is exact, while a name/artist
    text search can silently return the wrong track for a title that exists
    in multiple versions (remaster, live, cover, etc). It also avoids an
    extra Spotify call to fetch ISRC via `external_ids`, since the Spotify
    ID is already available and is at least as precise a key.
  - `GET /v1/track/{reccobeats_id}/audio-features` then returns the actual
    feature vector for that resolved track.

Field mapping onto this project's VibeOut/TrackVibe shape:
  - `energy` maps directly - the same 0-1 "intensity" concept the librosa
    fallback also produces.
  - `brightness` has no literal ReccoBeats analog (the librosa fallback's
    "brightness" is a spectral-centroid signal ReccoBeats doesn't expose).
    ReccoBeats' `valence` (0-1, sad/dark -> happy/bright mood) is used
    instead: for this project's bright/cheerful-vs-dark/moody vibe axis it's
    the closer semantic fit of what ReccoBeats does expose.
  - `tempo_bpm` maps directly from ReccoBeats' `tempo`.
  - `vibe_score` mirrors the librosa fallback's own formula: the mean of
    `energy` and `brightness` (here, valence).
  - `danceability`, `acousticness`, `instrumentalness`, `speechiness`,
    `loudness`, `key`, and `mode` map directly from ReccoBeats' own
    identically-named fields - confirmed present in the real
    `/audio-features` response. These have no librosa-fallback equivalent
    (see app/vibe_analysis.py), so they're only ever set on
    `source == "reccobeats"` rows; a track analyzed via librosa instead
    simply has them as None. They're also read defensively here (missing ->
    None) rather than with direct key access, in case a given ReccoBeats
    entry doesn't have full coverage for a track.

A track ReccoBeats has no data for (empty `/v1/track` result, or a 404 from
`/audio-features`) is not an error - `get_track_vibe` returns None so the
caller can fall through to the preview+librosa path. Any actual connectivity
problem, timeout, rate limit, or malformed response is likewise swallowed and
logged rather than raised, for the same reason.
"""

import logging

import httpx

logger = logging.getLogger(__name__)

SOURCE_LABEL = "reccobeats"

BASE_URL = "https://api.reccobeats.com"

# ReccoBeats has no documented SLA on latency, so a request that hangs must
# not stall the whole lookup - a fast, generous-enough timeout keeps this
# fallback path from becoming its own outage.
_REQUEST_TIMEOUT_SECONDS = 5.0


class ReccoBeatsError(Exception):
    """Raised internally for any non-2xx/404 ReccoBeats response.

    Never escapes `get_track_vibe` - it's caught there and turned into a
    logged warning plus a None return, exactly like a "no match" result.
    """


def _optional_float(data: dict, field: str) -> float | None:
    value = data.get(field)
    return None if value is None else float(value)


def _optional_int(data: dict, field: str) -> int | None:
    value = data.get(field)
    return None if value is None else int(value)


def _vibe_features_from_audio_features(data: dict) -> dict:
    energy = float(data["energy"])
    valence = float(data["valence"])
    tempo = float(data["tempo"])
    vibe_score = round((energy + valence) / 2, 4)
    return {
        "vibe_score": vibe_score,
        "energy": round(energy, 4),
        "brightness": round(valence, 4),
        "tempo_bpm": round(tempo, 2),
        "source": SOURCE_LABEL,
        "danceability": _optional_float(data, "danceability"),
        "acousticness": _optional_float(data, "acousticness"),
        "instrumentalness": _optional_float(data, "instrumentalness"),
        "speechiness": _optional_float(data, "speechiness"),
        "loudness": _optional_float(data, "loudness"),
        "key": _optional_int(data, "key"),
        "mode": _optional_int(data, "mode"),
    }


async def _resolve_reccobeats_id(client: httpx.AsyncClient, spotify_track_id: str) -> str | None:
    response = await client.get(f"{BASE_URL}/v1/track", params={"ids": spotify_track_id})
    if response.status_code != 200:
        raise ReccoBeatsError(f"track lookup failed (status {response.status_code})")

    content = response.json().get("content") or []
    if not content:
        return None
    return content[0]["id"]


async def _fetch_audio_features(client: httpx.AsyncClient, reccobeats_id: str) -> dict | None:
    response = await client.get(f"{BASE_URL}/v1/track/{reccobeats_id}/audio-features")
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise ReccoBeatsError(f"audio-features lookup failed (status {response.status_code})")
    return _vibe_features_from_audio_features(response.json())


async def get_track_vibe(
    spotify_track_id: str, http_client: httpx.AsyncClient | None = None
) -> dict | None:
    """Look up a track's vibe via ReccoBeats, keyed by its Spotify track ID.

    Returns a dict of vibe_score/energy/brightness/tempo_bpm/source, or None
    when ReccoBeats has no match or the request fails for any reason - see
    the module docstring and `ReccoBeatsError` for why this never raises.
    """
    client = http_client or httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS)
    try:
        reccobeats_id = await _resolve_reccobeats_id(client, spotify_track_id)
        if reccobeats_id is None:
            return None
        return await _fetch_audio_features(client, reccobeats_id)
    except (httpx.HTTPError, ReccoBeatsError, KeyError, ValueError, TypeError) as exc:
        logger.warning("ReccoBeats vibe lookup failed for track %s: %s", spotify_track_id, exc)
        return None
    finally:
        if http_client is None:
            await client.aclose()
