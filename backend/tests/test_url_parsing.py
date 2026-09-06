import pytest

from app.url_parsing import InvalidSpotifyUrlError, SpotifyRef, parse_spotify_reference

VALID_ALBUM_ID = "4aawyAB9vmqN3uQ7FjRGTy"
VALID_PLAYLIST_ID = "37i9dQZF1DXcBWIGoYBM5M"


@pytest.mark.parametrize(
    "url,expected",
    [
        (
            f"https://open.spotify.com/album/{VALID_ALBUM_ID}",
            SpotifyRef("album", VALID_ALBUM_ID),
        ),
        (
            f"https://open.spotify.com/album/{VALID_ALBUM_ID}?si=abc123",
            SpotifyRef("album", VALID_ALBUM_ID),
        ),
        (
            f"open.spotify.com/album/{VALID_ALBUM_ID}",
            SpotifyRef("album", VALID_ALBUM_ID),
        ),
        (
            f"https://open.spotify.com/intl-de/album/{VALID_ALBUM_ID}",
            SpotifyRef("album", VALID_ALBUM_ID),
        ),
        (
            f"https://open.spotify.com/playlist/{VALID_PLAYLIST_ID}",
            SpotifyRef("playlist", VALID_PLAYLIST_ID),
        ),
        (
            f"spotify:album:{VALID_ALBUM_ID}",
            SpotifyRef("album", VALID_ALBUM_ID),
        ),
        (
            f"spotify:playlist:{VALID_PLAYLIST_ID}",
            SpotifyRef("playlist", VALID_PLAYLIST_ID),
        ),
        (
            f"  https://open.spotify.com/album/{VALID_ALBUM_ID}  ",
            SpotifyRef("album", VALID_ALBUM_ID),
        ),
    ],
)
def test_parses_valid_references(url, expected):
    assert parse_spotify_reference(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "not a url at all",
        "https://example.com/album/4aawyAB9vmqN3uQ7FjRGTy",
        f"https://open.spotify.com/track/{VALID_ALBUM_ID}",
        "https://open.spotify.com/album/",
        "https://open.spotify.com/album/short-id",
        "spotify:track:4aawyAB9vmqN3uQ7FjRGTy",
        "spotify:album:",
    ],
)
def test_rejects_invalid_references(url):
    with pytest.raises(InvalidSpotifyUrlError):
        parse_spotify_reference(url)
