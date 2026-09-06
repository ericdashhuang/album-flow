import respx
from httpx import Response

ALBUM_ID = "4aawyAB9vmqN3uQ7FjRGTy"
PLAYLIST_ID = "37i9dQZF1DXcBWIGoYBM5M"

TOKEN_RESPONSE = {"access_token": "fake-token", "token_type": "Bearer", "expires_in": 3600}


def _mock_token(router: respx.MockRouter) -> None:
    router.post("https://accounts.spotify.com/api/token").mock(
        return_value=Response(200, json=TOKEN_RESPONSE)
    )


@respx.mock
def test_lookup_album_returns_clean_tracklist(client):
    _mock_token(respx)
    respx.get(f"https://api.spotify.com/v1/albums/{ALBUM_ID}").mock(
        return_value=Response(
            200,
            json={
                "name": "Test Album",
                "artists": [{"name": "Test Artist"}],
                "images": [{"url": "https://example.com/cover.jpg"}],
            },
        )
    )
    respx.get(url__regex=rf"https://api\.spotify\.com/v1/albums/{ALBUM_ID}/tracks.*").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "name": "Track One",
                        "artists": [{"name": "Test Artist"}],
                        "duration_ms": 200000,
                        "track_number": 1,
                    },
                    {
                        "name": "Track Two",
                        "artists": [{"name": "Test Artist"}, {"name": "Featured Artist"}],
                        "duration_ms": 180000,
                        "track_number": 2,
                    },
                ]
            },
        )
    )

    response = client.get(
        "/api/lookup", params={"url": f"https://open.spotify.com/album/{ALBUM_ID}"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["item_type"] == "album"
    assert body["name"] == "Test Album"
    assert body["owner"] == "Test Artist"
    assert body["cover_art_url"] == "https://example.com/cover.jpg"
    assert len(body["tracks"]) == 2
    assert body["tracks"][1]["artist"] == "Test Artist, Featured Artist"


@respx.mock
def test_lookup_playlist_skips_null_tracks(client):
    _mock_token(respx)
    respx.get(f"https://api.spotify.com/v1/playlists/{PLAYLIST_ID}").mock(
        return_value=Response(
            200,
            json={
                "name": "Test Playlist",
                "owner": {"display_name": "Test Owner"},
                "images": [{"url": "https://example.com/playlist.jpg"}],
            },
        )
    )
    respx.get(url__regex=rf"https://api\.spotify\.com/v1/playlists/{PLAYLIST_ID}/items.*").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "track": {
                            "name": "Playlist Track",
                            "artists": [{"name": "Someone"}],
                            "duration_ms": 210000,
                        }
                    },
                    {"track": None},
                ]
            },
        )
    )

    response = client.get(
        "/api/lookup", params={"url": f"https://open.spotify.com/playlist/{PLAYLIST_ID}"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["item_type"] == "playlist"
    assert body["owner"] == "Test Owner"
    assert len(body["tracks"]) == 1
    assert body["tracks"][0]["name"] == "Playlist Track"


def test_lookup_invalid_url_returns_400(client):
    response = client.get("/api/lookup", params={"url": "not-a-spotify-url"})
    assert response.status_code == 400
    assert "detail" in response.json()


@respx.mock
def test_lookup_spotify_404_returns_404(client):
    _mock_token(respx)
    respx.get(f"https://api.spotify.com/v1/albums/{ALBUM_ID}").mock(
        return_value=Response(404, json={"error": {"status": 404, "message": "not found"}})
    )

    response = client.get(
        "/api/lookup", params={"url": f"https://open.spotify.com/album/{ALBUM_ID}"}
    )

    assert response.status_code == 404


@respx.mock
def test_lookup_spotify_rate_limit_returns_429(client):
    _mock_token(respx)
    respx.get(f"https://api.spotify.com/v1/albums/{ALBUM_ID}").mock(
        return_value=Response(429, headers={"Retry-After": "5"})
    )

    response = client.get(
        "/api/lookup", params={"url": f"https://open.spotify.com/album/{ALBUM_ID}"}
    )

    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "5"
