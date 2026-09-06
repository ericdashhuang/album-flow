from app.schemas import LookupResult, TrackOut
from app.spotify_client import SpotifyClient
from app.url_parsing import SpotifyRef


def _largest_image_url(images: list[dict]) -> str | None:
    return images[0]["url"] if images else None


def _artist_names(artists: list[dict]) -> str:
    return ", ".join(artist["name"] for artist in artists)


async def _build_album_result(client: SpotifyClient, ref: SpotifyRef) -> LookupResult:
    album = await client.get_album(ref.item_id)
    tracks_page = await client.get_album_tracks(ref.item_id)

    tracks = [
        TrackOut(
            name=item["name"],
            artist=_artist_names(item["artists"]),
            duration_ms=item["duration_ms"],
            track_number=item["track_number"],
        )
        for item in tracks_page["items"]
    ]

    return LookupResult(
        item_type="album",
        spotify_id=ref.item_id,
        name=album["name"],
        owner=_artist_names(album["artists"]),
        cover_art_url=_largest_image_url(album["images"]),
        tracks=tracks,
    )


async def _build_playlist_result(client: SpotifyClient, ref: SpotifyRef) -> LookupResult:
    playlist = await client.get_playlist(ref.item_id)
    items_page = await client.get_playlist_items(ref.item_id)

    tracks = []
    for position, entry in enumerate(items_page["items"], start=1):
        track = entry.get("track")
        if track is None:
            continue
        tracks.append(
            TrackOut(
                name=track["name"],
                artist=_artist_names(track["artists"]),
                duration_ms=track["duration_ms"],
                track_number=position,
            )
        )

    owner = playlist.get("owner") or {}
    return LookupResult(
        item_type="playlist",
        spotify_id=ref.item_id,
        name=playlist["name"],
        owner=owner.get("display_name") or "Unknown",
        cover_art_url=_largest_image_url(playlist.get("images") or []),
        tracks=tracks,
    )


async def build_lookup_result(client: SpotifyClient, ref: SpotifyRef) -> LookupResult:
    if ref.item_type == "album":
        return await _build_album_result(client, ref)
    return await _build_playlist_result(client, ref)
