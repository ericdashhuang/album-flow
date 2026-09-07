import asyncio

import pytest
from sqlmodel import Session

from app.database import get_engine
from app.game_service import (
    NoSuitableAlbumError,
    RoundNotFinishedError,
    reveal_round,
    start_round,
    submit_guess,
)
from app.models import GameRound
from app.schemas import VibeOut

ARTIST = {"id": "artist-1", "name": "Test Artist"}


@pytest.fixture()
def session(client):
    # `client` fixture (from conftest) already calls init_db() against the
    # shared in-memory SQLite engine.
    with Session(get_engine()) as db_session:
        yield db_session


class FakeSpotifyClient:
    """Minimal stand-in for SpotifyClient - game_service only needs these
    three async methods, so tests can skip HTTP mocking entirely."""

    def __init__(self, albums: list[dict], tracks_by_album: dict[str, list[dict]]):
        self._albums = albums
        self._tracks_by_album = tracks_by_album

    async def search_artist(self, name: str) -> dict:
        return {"artists": {"items": [ARTIST]}}

    async def get_artist_albums(self, artist_id: str, limit: int = 50) -> dict:
        return {"items": self._albums}

    async def get_album_tracks(self, album_id: str, limit: int = 50) -> dict:
        return {"items": self._tracks_by_album[album_id]}


def _album(album_id: str, name: str) -> dict:
    return {"id": album_id, "name": name, "album_type": "album", "images": []}


def _track_item(track_id: str, number: int) -> dict:
    return {
        "id": track_id,
        "name": f"Secret Track {number} ({track_id})",
        "track_number": number,
        "preview_url": None,
    }


def _good_vibe(**overrides) -> VibeOut:
    base = dict(
        vibe_score=0.5,
        energy=0.5,
        brightness=0.5,
        tempo_bpm=120.0,
        source="reccobeats",
        danceability=0.6,
        acousticness=0.3,
        instrumentalness=0.1,
        speechiness=0.05,
        loudness=-7.0,
        key=4,
        mode=1,
    )
    base.update(overrides)
    return VibeOut(**base)


def test_sparse_target_is_rerolled_for_a_better_album(session, monkeypatch):
    monkeypatch.setattr("app.game_service.random.shuffle", lambda seq: None)

    albums = [
        _album("sparse-a", "Sparse Album"),
        _album("sparse-b", "Also Sparse"),
        _album("good-c", "Good Album"),
    ]
    tracks_by_album = {
        "sparse-a": [_track_item("sa1", 1), _track_item("sa2", 2)],
        "sparse-b": [_track_item("sb1", 1), _track_item("sb2", 2)],
        "good-c": [_track_item("gc1", 1), _track_item("gc2", 2)],
    }
    vibe_by_track = {"gc1": _good_vibe(), "gc2": _good_vibe()}

    async def fake_get_or_compute_vibe(session, track_id, preview_url):
        return vibe_by_track.get(track_id)

    monkeypatch.setattr("app.game_service.get_or_compute_vibe", fake_get_or_compute_vibe)

    client_stub = FakeSpotifyClient(albums, tracks_by_album)
    result = asyncio.run(start_round(session, client_stub, "Test Artist"))

    row = session.get(GameRound, result.round_id)
    assert row.target_album_id == "good-c"
    # The sparse albums were tried and rejected, not just skipped - confirm
    # the round still lists all three as guessable options.
    option_names = {option["name"] for option in result.album_options}
    assert option_names == {"Sparse Album", "Also Sparse", "Good Album"}


def test_no_album_has_enough_data_raises(session, monkeypatch):
    monkeypatch.setattr("app.game_service.random.shuffle", lambda seq: None)
    albums = [_album("a", "A"), _album("b", "B"), _album("c", "C")]
    tracks_by_album = {
        "a": [_track_item("a1", 1), _track_item("a2", 2)],
        "b": [_track_item("b1", 1), _track_item("b2", 2)],
        "c": [_track_item("c1", 1), _track_item("c2", 2)],
    }

    async def fake_get_or_compute_vibe(session, track_id, preview_url):
        return None

    monkeypatch.setattr("app.game_service.get_or_compute_vibe", fake_get_or_compute_vibe)
    client_stub = FakeSpotifyClient(albums, tracks_by_album)

    with pytest.raises(NoSuitableAlbumError):
        asyncio.run(start_round(session, client_stub, "Test Artist"))


def test_hint_metric_revealed_every_second_wrong_guess(session, monkeypatch):
    monkeypatch.setattr("app.game_service.random.shuffle", lambda seq: None)
    albums = [
        _album("target", "Target Album"),
        _album("wrong-1", "Wrong One"),
        _album("wrong-2", "Wrong Two"),
    ]
    tracks_by_album = {
        "target": [_track_item("t1", 1), _track_item("t2", 2)],
        "wrong-1": [_track_item("w1", 1)],
        "wrong-2": [_track_item("w2", 1)],
    }

    async def fake_get_or_compute_vibe(session, track_id, preview_url):
        return _good_vibe()

    monkeypatch.setattr("app.game_service.get_or_compute_vibe", fake_get_or_compute_vibe)
    client_stub = FakeSpotifyClient(albums, tracks_by_album)
    result = asyncio.run(start_round(session, client_stub, "Test Artist"))

    # First wrong guess: no hint yet.
    guess1 = submit_guess(session, result.round_id, "wrong-1")
    assert guess1.correct is False
    assert guess1.wrong_guess_count == 1
    assert guess1.newly_revealed_metric is None

    # Second wrong guess: crosses the first threshold -> danceability.
    guess2 = submit_guess(session, result.round_id, "wrong-2")
    assert guess2.correct is False
    assert guess2.wrong_guess_count == 2
    assert guess2.newly_revealed_metric is not None
    assert guess2.newly_revealed_metric["metric"] == "danceability"
    assert guess2.newly_revealed_metric["data"] == [
        {"track_number": 1, "value": 0.6, "mode": None},
        {"track_number": 2, "value": 0.6, "mode": None},
    ]

    # Third wrong guess: no new threshold crossed.
    guess3 = submit_guess(session, result.round_id, "wrong-1")
    assert guess3.wrong_guess_count == 3
    assert guess3.newly_revealed_metric is None

    # Fourth wrong guess: crosses the second threshold -> acousticness.
    guess4 = submit_guess(session, result.round_id, "wrong-2")
    assert guess4.wrong_guess_count == 4
    assert guess4.newly_revealed_metric["metric"] == "acousticness"

    # A correct guess ends the round without leaking a hint payload.
    correct = submit_guess(session, result.round_id, "target")
    assert correct.correct is True
    assert correct.newly_revealed_metric is None


def test_reveal_before_solved_requires_give_up(session, monkeypatch):
    monkeypatch.setattr("app.game_service.random.shuffle", lambda seq: None)
    albums = [
        _album("target", "Target Album"),
        _album("wrong-1", "Wrong One"),
        _album("wrong-2", "Wrong Two"),
    ]
    tracks_by_album = {
        "target": [_track_item("t1", 1)],
        "wrong-1": [_track_item("w1", 1)],
        "wrong-2": [_track_item("w2", 1)],
    }

    async def fake_get_or_compute_vibe(session, track_id, preview_url):
        return _good_vibe()

    monkeypatch.setattr("app.game_service.get_or_compute_vibe", fake_get_or_compute_vibe)
    client_stub = FakeSpotifyClient(albums, tracks_by_album)
    result = asyncio.run(start_round(session, client_stub, "Test Artist"))

    with pytest.raises(RoundNotFinishedError):
        reveal_round(session, result.round_id)

    revealed = reveal_round(session, result.round_id, give_up=True)
    assert revealed.album_name == "Target Album"
    assert revealed.tracks[0]["name"] == "Secret Track 1 (t1)"


def test_round_creation_never_leaks_target_or_track_names(session, monkeypatch):
    monkeypatch.setattr("app.game_service.random.shuffle", lambda seq: None)
    albums = [
        _album("target", "Target Album"),
        _album("wrong-1", "Wrong One"),
        _album("wrong-2", "Wrong Two"),
    ]
    tracks_by_album = {
        "target": [_track_item("t1", 1), _track_item("t2", 2)],
        "wrong-1": [_track_item("w1", 1)],
        "wrong-2": [_track_item("w2", 1)],
    }

    async def fake_get_or_compute_vibe(session, track_id, preview_url):
        return _good_vibe()

    monkeypatch.setattr("app.game_service.get_or_compute_vibe", fake_get_or_compute_vibe)
    client_stub = FakeSpotifyClient(albums, tracks_by_album)
    result = asyncio.run(start_round(session, client_stub, "Test Artist"))

    # hints must only ever carry track_number + vibe_score - never a name.
    for hint in result.hints:
        assert set(hint.keys()) == {"track_number", "vibe_score"}

    # A wrong guess's hint payload must only ever carry track_number/value/mode.
    guess = submit_guess(session, result.round_id, "wrong-1")
    guess2 = submit_guess(session, result.round_id, "wrong-2")
    assert guess2.newly_revealed_metric is not None
    for point in guess2.newly_revealed_metric["data"]:
        assert set(point.keys()) == {"track_number", "value", "mode"}
