from pydantic import BaseModel


class VibeOut(BaseModel):
    """Computed vibe/energy signal for one track. `source` distinguishes which
    pipeline produced it - see app/vibe_service.py for the lookup order and
    app/reccobeats_client.py / app/vibe_analysis.py for how each is derived.
    """

    vibe_score: float
    energy: float
    brightness: float
    tempo_bpm: float
    source: str


class TrackOut(BaseModel):
    spotify_id: str
    name: str
    artist: str
    duration_ms: int
    track_number: int
    preview_url: str | None = None
    vibe: VibeOut | None = None


class LookupResult(BaseModel):
    item_type: str
    spotify_id: str
    name: str
    owner: str  # artist name for an album, or playlist owner's display name for a playlist
    cover_art_url: str | None
    tracks: list[TrackOut]
