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

    The columns from `danceability` onward are only ever populated when
    `source == "reccobeats"` - the librosa fallback has no equivalent signal
    for them, so they stay None for librosa-sourced rows.
    """

    spotify_track_id: str = Field(primary_key=True)
    vibe_score: float
    energy: float
    brightness: float
    tempo_bpm: float
    source: str
    danceability: float | None = None
    acousticness: float | None = None
    instrumentalness: float | None = None
    speechiness: float | None = None
    loudness: float | None = None
    key: int | None = None
    mode: int | None = None
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GameRound(SQLModel, table=True):
    """Server-side state for one album-guessing round.

    This row is the ONLY place the target album's identity and its track
    names live until the round is solved (or given up) - see
    app/game_service.py's module docstring. `tracks_json` and
    `album_options_json` are stored as plain JSON text (rather than a related
    table) since they're captured once at round-start and never queried by
    field, only read back whole by the round they belong to.
    """

    id: str = Field(primary_key=True)
    artist_name: str
    target_album_id: str
    target_album_name: str
    target_album_image_url: str | None = None
    tracks_json: str
    album_options_json: str
    eliminated_album_ids_json: str = "[]"
    wrong_guess_count: int = 0
    revealed_hint_level: int = 0
    solved: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
