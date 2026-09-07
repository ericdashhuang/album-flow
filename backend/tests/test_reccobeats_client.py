import asyncio

import httpx
import respx
from httpx import Response

from app.reccobeats_client import get_track_vibe

TRACK_ID = "06HL4z0CvFAxyc27GXpf02"
RECCO_ID = "2670c328-c40f-45f4-80df-f48b29296deb"


@respx.mock
def test_match_returns_mapped_features():
    respx.get("https://api.reccobeats.com/v1/track", params={"ids": TRACK_ID}).mock(
        return_value=Response(200, json={"content": [{"id": RECCO_ID}]})
    )
    respx.get(f"https://api.reccobeats.com/v1/track/{RECCO_ID}/audio-features").mock(
        return_value=Response(
            200,
            json={
                "id": RECCO_ID,
                "energy": 0.8,
                "valence": 0.3,
                "tempo": 140.0,
                "danceability": 0.5,
                "acousticness": 0.2,
                "instrumentalness": 0.05,
                "speechiness": 0.04,
                "loudness": -6.5,
                "key": 7,
                "mode": 1,
            },
        )
    )

    result = asyncio.run(get_track_vibe(TRACK_ID))

    assert result == {
        "vibe_score": round((0.8 + 0.3) / 2, 4),
        "energy": 0.8,
        "brightness": 0.3,
        "tempo_bpm": 140.0,
        "source": "reccobeats",
        "danceability": 0.5,
        "acousticness": 0.2,
        "instrumentalness": 0.05,
        "speechiness": 0.04,
        "loudness": -6.5,
        "key": 7,
        "mode": 1,
    }


@respx.mock
def test_no_search_match_returns_none():
    respx.get("https://api.reccobeats.com/v1/track", params={"ids": TRACK_ID}).mock(
        return_value=Response(200, json={"content": []})
    )

    result = asyncio.run(get_track_vibe(TRACK_ID))

    assert result is None


@respx.mock
def test_audio_features_not_found_returns_none():
    respx.get("https://api.reccobeats.com/v1/track", params={"ids": TRACK_ID}).mock(
        return_value=Response(200, json={"content": [{"id": RECCO_ID}]})
    )
    respx.get(f"https://api.reccobeats.com/v1/track/{RECCO_ID}/audio-features").mock(
        return_value=Response(404)
    )

    result = asyncio.run(get_track_vibe(TRACK_ID))

    assert result is None


@respx.mock
def test_rate_limited_response_returns_none_gracefully():
    respx.get("https://api.reccobeats.com/v1/track", params={"ids": TRACK_ID}).mock(
        return_value=Response(429)
    )

    result = asyncio.run(get_track_vibe(TRACK_ID))

    assert result is None


@respx.mock
def test_network_error_returns_none_gracefully():
    respx.get("https://api.reccobeats.com/v1/track", params={"ids": TRACK_ID}).mock(
        side_effect=httpx.ConnectTimeout("timed out")
    )

    result = asyncio.run(get_track_vibe(TRACK_ID))

    assert result is None


@respx.mock
def test_malformed_audio_features_response_returns_none():
    respx.get("https://api.reccobeats.com/v1/track", params={"ids": TRACK_ID}).mock(
        return_value=Response(200, json={"content": [{"id": RECCO_ID}]})
    )
    respx.get(f"https://api.reccobeats.com/v1/track/{RECCO_ID}/audio-features").mock(
        return_value=Response(200, json={"id": RECCO_ID})
    )

    result = asyncio.run(get_track_vibe(TRACK_ID))

    assert result is None
