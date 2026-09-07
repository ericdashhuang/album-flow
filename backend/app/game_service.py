"""Server-side orchestration for the album-guessing game.

The whole point of this module is that the target album's identity and its
track names must never reach the frontend before a round legitimately ends:
a browser can trivially inspect network responses, so if the answer were in
the initial round-creation or guess response, the game would be broken on
the first round. `GameRound` (app/models.py) is the only place that data
lives - everything this module hands back for an in-progress round
(`RoundStart`, `GuessResult`) must be reviewed against that constraint;
`RevealResult` is the sole exception, and only after `GameRound.solved` (or
an explicit give-up) is true.

Reuses the existing Spotify/vibe pipeline rather than duplicating it -
`SpotifyClient` (app/spotify_client.py) for artist/album/track lookups and
`get_or_compute_vibe` (app/vibe_service.py) for the per-track vibe metrics,
cache included.
"""

import json
import random
import uuid
from dataclasses import dataclass
from typing import Protocol

from sqlmodel import Session

from app.models import GameRound
from app.vibe_service import get_or_compute_vibe

# How many real albums an artist needs before a round is even worth starting.
MIN_ALBUMS_FOR_ROUND = 3

# How many candidate albums to try before giving up on finding one with
# enough computed vibe data to make a decent puzzle.
MAX_TARGET_ATTEMPTS = 3

# An album qualifies as a target only if at least this fraction of its
# tracks have some computed vibe data (from either ReccoBeats or librosa).
MIN_VIBE_COVERAGE = 0.5

# Every 2nd wrong guess reveals the next metric in this order. Energy/valence
# (the base vibe-score line) is visible from the start and is not part of
# this reveal sequence.
HINT_METRIC_ORDER = [
    "danceability",
    "acousticness",
    "instrumentalness",
    "speechiness",
    "loudness",
    "key",
]


class ArtistNotFoundError(Exception):
    """No Spotify artist matched the given name."""


class NotEnoughAlbumsError(Exception):
    """The artist doesn't have enough real studio albums for a round."""


class NoSuitableAlbumError(Exception):
    """No candidate album had enough computed vibe data for a round."""


class RoundNotFoundError(Exception):
    """No GameRound exists with the given id."""


class RoundNotFinishedError(Exception):
    """Reveal was requested before the round was solved (and no give-up)."""


class SpotifyClientProtocol(Protocol):
    """The subset of SpotifyClient this module depends on - lets tests pass
    a lightweight stub instead of a real HTTP-backed client."""

    async def search_artist(self, name: str) -> dict: ...

    async def get_artist_albums(self, artist_id: str, limit: int = 50) -> dict: ...

    async def get_album_tracks(self, album_id: str, limit: int = 50) -> dict: ...


def _dedupe_albums_by_name(items: list[dict]) -> list[dict]:
    """Spotify's artist-albums endpoint frequently lists the same album
    multiple times (regional reissues, remasters) with distinct IDs but an
    identical name. A duplicate name would be a confusing, distinguishable-
    only-by-luck pair of guess options, so only the first occurrence of each
    name is kept."""
    seen: set[str] = set()
    deduped = []
    for item in items:
        key = item["name"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


async def _fetch_real_albums(client: SpotifyClientProtocol, artist_id: str) -> list[dict]:
    page = await client.get_artist_albums(artist_id)
    albums = [item for item in page.get("items", []) if item.get("album_type") == "album"]
    return _dedupe_albums_by_name(albums)


async def _build_track_data(
    session: Session, client: SpotifyClientProtocol, album_id: str
) -> list[dict]:
    tracks_page = await client.get_album_tracks(album_id)
    tracks = []
    for item in tracks_page["items"]:
        vibe = await get_or_compute_vibe(session, item["id"], item.get("preview_url"))
        tracks.append(
            {
                "spotify_id": item["id"],
                "name": item["name"],
                "track_number": item["track_number"],
                "vibe": vibe.model_dump() if vibe else None,
            }
        )
    return tracks


def _vibe_coverage(tracks: list[dict]) -> float:
    if not tracks:
        return 0.0
    with_vibe = sum(1 for track in tracks if track["vibe"] is not None)
    return with_vibe / len(tracks)


def _album_image_url(album: dict) -> str | None:
    images = album.get("images") or []
    return images[0]["url"] if images else None


@dataclass
class RoundStart:
    round_id: str
    artist_name: str
    album_options: list[dict]
    track_count: int
    hints: list[dict]


async def start_round(
    session: Session, client: SpotifyClientProtocol, artist_name: str
) -> RoundStart:
    """Resolve an artist by name and start a round in one call.

    Picks a random target album, rerolling (bounded by MAX_TARGET_ATTEMPTS)
    if the chosen one has too little computed vibe data to make a decent
    puzzle. Raises ArtistNotFoundError / NotEnoughAlbumsError /
    NoSuitableAlbumError for the corresponding failure cases - see
    app/main.py for how those map to HTTP responses.
    """
    search = await client.search_artist(artist_name)
    artists = search.get("artists", {}).get("items", [])
    if not artists:
        raise ArtistNotFoundError(f"No Spotify artist found for '{artist_name}'.")
    artist = artists[0]

    albums = await _fetch_real_albums(client, artist["id"])
    if len(albums) < MIN_ALBUMS_FOR_ROUND:
        raise NotEnoughAlbumsError(
            f"{artist['name']} doesn't have enough real studio albums for a round."
        )

    candidates = albums.copy()
    random.shuffle(candidates)

    target_album: dict | None = None
    target_tracks: list[dict] | None = None
    for album in candidates[:MAX_TARGET_ATTEMPTS]:
        tracks = await _build_track_data(session, client, album["id"])
        if _vibe_coverage(tracks) >= MIN_VIBE_COVERAGE:
            target_album = album
            target_tracks = tracks
            break

    if target_album is None or target_tracks is None:
        raise NoSuitableAlbumError(
            f"Couldn't find an album from {artist['name']} with enough vibe data for a round."
        )

    round_id = uuid.uuid4().hex
    options = [{"spotify_id": album["id"], "name": album["name"]} for album in albums]
    random.shuffle(options)

    row = GameRound(
        id=round_id,
        artist_name=artist["name"],
        target_album_id=target_album["id"],
        target_album_name=target_album["name"],
        target_album_image_url=_album_image_url(target_album),
        tracks_json=json.dumps(target_tracks),
        album_options_json=json.dumps(options),
    )
    session.add(row)
    session.commit()

    ordered_tracks = sorted(target_tracks, key=lambda t: t["track_number"])
    hints = [
        {
            "track_number": track["track_number"],
            "vibe_score": (track["vibe"] or {}).get("vibe_score"),
        }
        for track in ordered_tracks
    ]

    return RoundStart(
        round_id=round_id,
        artist_name=artist["name"],
        album_options=options,
        track_count=len(target_tracks),
        hints=hints,
    )


def _get_round(session: Session, round_id: str) -> GameRound:
    row = session.get(GameRound, round_id)
    if row is None:
        raise RoundNotFoundError(f"No active round with id {round_id}.")
    return row


@dataclass
class GuessResult:
    correct: bool
    wrong_guess_count: int
    newly_revealed_metric: dict | None


def submit_guess(session: Session, round_id: str, guessed_album_id: str) -> GuessResult:
    """Check a guess server-side and, on a wrong guess, cross any newly
    unlocked hint threshold. Never returns the target's identity or any
    track name, even on a correct guess - that's reveal_round's job."""
    row = _get_round(session, round_id)

    if row.solved or guessed_album_id == row.target_album_id:
        row.solved = True
        session.add(row)
        session.commit()
        return GuessResult(
            correct=True, wrong_guess_count=row.wrong_guess_count, newly_revealed_metric=None
        )

    row.wrong_guess_count += 1
    new_hint_level = min(row.wrong_guess_count // 2, len(HINT_METRIC_ORDER))

    newly_revealed = None
    if new_hint_level > row.revealed_hint_level:
        metric_name = HINT_METRIC_ORDER[new_hint_level - 1]
        tracks = sorted(json.loads(row.tracks_json), key=lambda t: t["track_number"])
        newly_revealed = {
            "metric": metric_name,
            "data": [
                {
                    "track_number": track["track_number"],
                    "value": (track["vibe"] or {}).get(metric_name),
                    "mode": (track["vibe"] or {}).get("mode") if metric_name == "key" else None,
                }
                for track in tracks
            ],
        }
        row.revealed_hint_level = new_hint_level

    session.add(row)
    session.commit()

    return GuessResult(
        correct=False,
        wrong_guess_count=row.wrong_guess_count,
        newly_revealed_metric=newly_revealed,
    )


@dataclass
class RevealResult:
    album_name: str
    album_image_url: str | None
    artist_name: str
    tracks: list[dict]
    revealed_metrics: list[str]


def reveal_round(session: Session, round_id: str, give_up: bool = False) -> RevealResult:
    """Reveal a round's answer - callable once the round is solved, or with
    `give_up=True` to end it early without a correct guess."""
    row = _get_round(session, round_id)

    if not row.solved:
        if not give_up:
            raise RoundNotFinishedError("This round hasn't been solved yet.")
        row.solved = True
        session.add(row)
        session.commit()

    tracks = sorted(json.loads(row.tracks_json), key=lambda t: t["track_number"])
    revealed_metrics = HINT_METRIC_ORDER[: row.revealed_hint_level]

    def _track_out(track: dict) -> dict:
        vibe = track["vibe"] or {}
        out = {
            "track_number": track["track_number"],
            "name": track["name"],
            "vibe_score": vibe.get("vibe_score"),
        }
        for metric in revealed_metrics:
            out[metric] = vibe.get(metric)
        if "key" in revealed_metrics:
            out["mode"] = vibe.get("mode")
        return out

    return RevealResult(
        album_name=row.target_album_name,
        album_image_url=row.target_album_image_url,
        artist_name=row.artist_name,
        tracks=[_track_out(t) for t in tracks],
        revealed_metrics=revealed_metrics,
    )
