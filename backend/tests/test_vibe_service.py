import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session

from app.database import get_engine
from app.vibe_analysis import AudioAnalysisError, VibeFeatures
from app.vibe_service import get_or_compute_vibe

FAKE_LIBROSA_FEATURES = VibeFeatures(vibe_score=0.5, energy=0.4, brightness=0.6, tempo_bpm=120.0)
FAKE_RECCOBEATS_FEATURES = {
    "vibe_score": 0.65,
    "energy": 0.7,
    "brightness": 0.6,
    "tempo_bpm": 128.0,
    "source": "reccobeats",
}


@pytest.fixture()
def session(client):
    # `client` fixture (from conftest) already calls init_db() against the
    # shared in-memory SQLite engine.
    with Session(get_engine()) as db_session:
        yield db_session


@patch("app.vibe_service.get_track_vibe", new_callable=AsyncMock, return_value=FAKE_RECCOBEATS_FEATURES)
def test_reccobeats_match_is_used_and_cached(mock_get_track_vibe, session):
    first = asyncio.run(get_or_compute_vibe(session, "track-recco", None))
    second = asyncio.run(get_or_compute_vibe(session, "track-recco", None))

    assert first == second
    assert first.vibe_score == 0.65
    assert first.source == "reccobeats"
    mock_get_track_vibe.assert_awaited_once()


@patch("app.vibe_service.analyze_audio", return_value=FAKE_LIBROSA_FEATURES)
@patch("app.vibe_service.download_preview_clip", new_callable=AsyncMock, return_value=b"fake-mp3")
@patch("app.vibe_service.get_track_vibe", new_callable=AsyncMock, return_value=None)
def test_reccobeats_miss_falls_back_to_librosa(
    mock_get_track_vibe, mock_download, mock_analyze, session
):
    result = asyncio.run(
        get_or_compute_vibe(session, "track-abc", "https://example.com/preview.mp3")
    )

    assert result.vibe_score == 0.5
    assert result.source == "librosa_fallback"
    mock_get_track_vibe.assert_awaited_once()
    mock_download.assert_awaited_once()
    mock_analyze.assert_called_once()


@patch("app.vibe_service.get_track_vibe", new_callable=AsyncMock, return_value=None)
def test_second_lookup_of_same_track_does_not_reanalyze(mock_get_track_vibe, session):
    with patch(
        "app.vibe_service.analyze_audio", return_value=FAKE_LIBROSA_FEATURES
    ) as mock_analyze, patch(
        "app.vibe_service.download_preview_clip",
        new_callable=AsyncMock,
        return_value=b"fake-mp3",
    ) as mock_download:
        first = asyncio.run(
            get_or_compute_vibe(session, "track-second-lookup", "https://example.com/preview.mp3")
        )
        second = asyncio.run(
            get_or_compute_vibe(session, "track-second-lookup", "https://example.com/preview.mp3")
        )

    assert first == second
    assert first.vibe_score == 0.5
    mock_download.assert_awaited_once()
    mock_analyze.assert_called_once()
    assert mock_get_track_vibe.await_count == 1


@patch("app.vibe_service.get_track_vibe", new_callable=AsyncMock, return_value=None)
def test_analysis_failure_returns_none_gracefully(mock_get_track_vibe, session):
    with patch("app.vibe_service.analyze_audio") as mock_analyze, patch(
        "app.vibe_service.download_preview_clip",
        new_callable=AsyncMock,
        return_value=b"junk",
    ) as mock_download:
        mock_analyze.side_effect = AudioAnalysisError("decode failed")

        result = asyncio.run(
            get_or_compute_vibe(session, "track-bad-audio", "https://example.com/bad.mp3")
        )

    assert result is None


@patch("app.vibe_service.analyze_audio")
@patch("app.vibe_service.download_preview_clip", new_callable=AsyncMock)
@patch("app.vibe_service.get_track_vibe", new_callable=AsyncMock, return_value=None)
def test_both_sources_unavailable_returns_none(
    mock_get_track_vibe, mock_download, mock_analyze, session
):
    result = asyncio.run(get_or_compute_vibe(session, "track-no-preview", None))

    assert result is None
    mock_get_track_vibe.assert_awaited_once()
    mock_download.assert_not_awaited()
    mock_analyze.assert_not_called()
