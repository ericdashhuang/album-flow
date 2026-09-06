from pydantic import BaseModel


class VibeOut(BaseModel):
    """Computed vibe/energy signal for one track. See app/vibe_analysis.py for
    how these values are derived and why they're a librosa-based approximation
    rather than Spotify's (now-unavailable) audio-features.
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
