from pydantic import BaseModel


class TrackOut(BaseModel):
    name: str
    artist: str
    duration_ms: int
    track_number: int


class LookupResult(BaseModel):
    item_type: str
    spotify_id: str
    name: str
    owner: str  # artist name for an album, or playlist owner's display name for a playlist
    cover_art_url: str | None
    tracks: list[TrackOut]
