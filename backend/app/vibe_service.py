"""Orchestrates per-track vibe analysis with a Postgres-backed cache.

Keeps `app/vibe_analysis.py` and `app/reccobeats_client.py` (pure lookup/
analysis, no database) free of database concerns, and keeps this layer free
of Spotify concerns - it only needs a track ID and an optional preview URL.

Vibe source order: cache -> ReccoBeats (see app/reccobeats_client.py) ->
preview+librosa (see app/vibe_analysis.py) -> None. ReccoBeats is primary
because it needs no audio at all, and real-world Spotify preview-URL
availability has turned out to be far rarer than originally assumed (see the
project AGENTS.md); the preview+librosa path remains as a fallback for
whenever ReccoBeats has no data for a track.
"""

import logging

from sqlmodel import Session

from app.models import TrackVibe
from app.reccobeats_client import get_track_vibe
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

    Tries ReccoBeats first (no preview clip needed), then falls back to the
    preview+librosa path if ReccoBeats has no match and a preview URL exists.
    Returns None (never raises) when none of that is available - a missing
    vibe should never fail the whole lookup request.
    """
    cached = session.get(TrackVibe, spotify_track_id)
    if cached is not None:
        return _to_vibe_out(cached)

    features = await get_track_vibe(spotify_track_id)

    if features is None and preview_url:
        try:
            clip_bytes = await download_preview_clip(preview_url)
            analyzed = analyze_audio(clip_bytes)
        except (PreviewDownloadError, AudioAnalysisError) as exc:
            logger.warning("Vibe analysis unavailable for track %s: %s", spotify_track_id, exc)
        else:
            features = {
                "vibe_score": analyzed.vibe_score,
                "energy": analyzed.energy,
                "brightness": analyzed.brightness,
                "tempo_bpm": analyzed.tempo_bpm,
                "source": analyzed.source,
            }

    if features is None:
        return None

    row = TrackVibe(spotify_track_id=spotify_track_id, **features)
    session.add(row)
    session.commit()
    return _to_vibe_out(row)
