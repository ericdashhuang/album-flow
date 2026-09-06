from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class LookupLog(SQLModel, table=True):
    """A record of each successful album/playlist lookup, for basic usage visibility."""

    id: int | None = Field(default=None, primary_key=True)
    item_type: str
    spotify_id: str
    name: str
    looked_up_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrackVibe(SQLModel, table=True):
    """Cached vibe/energy analysis for one Spotify track, keyed by track ID so the
    same track is never re-analyzed just because it shows up in a different
    album or playlist lookup.
    """

    spotify_track_id: str = Field(primary_key=True)
    vibe_score: float
    energy: float
    brightness: float
    tempo_bpm: float
    source: str
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
