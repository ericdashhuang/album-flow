"""Orchestrates per-track vibe analysis with a Postgres-backed cache.

Keeps `app/vibe_analysis.py` (pure audio download/analysis) free of database
concerns, and keeps this layer free of Spotify concerns - it only needs a
track ID and an optional preview URL.
"""

import logging

from sqlmodel import Session

from app.models import TrackVibe
from app.schemas import VibeOut
from app.vibe_analysis import (
    AudioAnalysisError,
    PreviewDownloadError,
    analyze_audio,
    download_preview_clip,
)

logger = logging.getLogger(__name__)


def _to_vibe_out(row: TrackVibe) -> VibeOut:
    return VibeOut(
        vibe_score=row.vibe_score,
        energy=row.energy,
        brightness=row.brightness,
        tempo_bpm=row.tempo_bpm,
        source=row.source,
    )


async def get_or_compute_vibe(
    session: Session, spotify_track_id: str, preview_url: str | None
) -> VibeOut | None:
    """Return the cached vibe for a track, computing and caching it if needed.

    Returns None (never raises) when no preview clip is available or the
    download/analysis fails - a missing vibe should never fail the whole
    lookup request.
    """
    cached = session.get(TrackVibe, spotify_track_id)
    if cached is not None:
        return _to_vibe_out(cached)

    if not preview_url:
        return None

    try:
        clip_bytes = await download_preview_clip(preview_url)
        features = analyze_audio(clip_bytes)
    except (PreviewDownloadError, AudioAnalysisError) as exc:
        logger.warning("Vibe analysis unavailable for track %s: %s", spotify_track_id, exc)
        return None

    row = TrackVibe(
        spotify_track_id=spotify_track_id,
        vibe_score=features.vibe_score,
        energy=features.energy,
        brightness=features.brightness,
        tempo_bpm=features.tempo_bpm,
        source=features.source,
    )
    session.add(row)
    session.commit()
    return _to_vibe_out(row)
