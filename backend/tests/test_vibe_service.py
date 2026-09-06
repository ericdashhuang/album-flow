import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session

from app.database import get_engine
from app.vibe_analysis import AudioAnalysisError, VibeFeatures
from app.vibe_service import get_or_compute_vibe

FAKE_FEATURES = VibeFeatures(vibe_score=0.5, energy=0.4, brightness=0.6, tempo_bpm=120.0)


@pytest.fixture()
def session(client):
    # `client` fixture (from conftest) already calls init_db() against the
    # shared in-memory SQLite engine.
    with Session(get_engine()) as db_session:
        yield db_session


@patch("app.vibe_service.analyze_audio", return_value=FAKE_FEATURES)
@patch("app.vibe_service.download_preview_clip", new_callable=AsyncMock, return_value=b"fake-mp3")
def test_second_lookup_of_same_track_does_not_reanalyze(mock_download, mock_analyze, session):
    first = asyncio.run(
        get_or_compute_vibe(session, "track-abc", "https://example.com/preview.mp3")
    )
    second = asyncio.run(
        get_or_compute_vibe(session, "track-abc", "https://example.com/preview.mp3")
    )

    assert first == second
    assert first.vibe_score == 0.5
    mock_download.assert_awaited_once()
    mock_analyze.assert_called_once()


@patch("app.vibe_service.analyze_audio")
@patch("app.vibe_service.download_preview_clip", new_callable=AsyncMock)
def test_missing_preview_url_returns_none_without_analysis(mock_download, mock_analyze, session):
    result = asyncio.run(get_or_compute_vibe(session, "track-no-preview", None))

    assert result is None
    mock_download.assert_not_awaited()
    mock_analyze.assert_not_called()


@patch("app.vibe_service.analyze_audio")
@patch("app.vibe_service.download_preview_clip", new_callable=AsyncMock, return_value=b"junk")
def test_analysis_failure_returns_none_gracefully(mock_download, mock_analyze, session):
    mock_analyze.side_effect = AudioAnalysisError("decode failed")

    result = asyncio.run(
        get_or_compute_vibe(session, "track-bad-audio", "https://example.com/bad.mp3")
    )

    assert result is None
