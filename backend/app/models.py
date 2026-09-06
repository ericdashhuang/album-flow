from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class LookupLog(SQLModel, table=True):
    """A record of each successful album/playlist lookup, for basic usage visibility."""

    id: int | None = Field(default=None, primary_key=True)
    item_type: str
    spotify_id: str
    name: str
    looked_up_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
