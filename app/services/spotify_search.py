import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from app.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

_client = None


def get_client() -> spotipy.Spotify:
    global _client
    if _client is None:
        if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
            raise RuntimeError(
                "SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET nao configurados no .env"
            )
        auth = SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET
        )
        _client = spotipy.Spotify(client_credentials_manager=auth)
    return _client


def search_tracks(query: str, limit: int = 10) -> list[dict]:
    sp = get_client()
    results = sp.search(q=query, type="track", limit=limit)
    tracks = results.get("tracks", {}).get("items", [])

    return [
        {
            "source": "spotify",
            "id": track["id"],
            "title": track["name"],
            "artist": ", ".join(a["name"] for a in track["artists"]),
            "album": track["album"]["name"],
            "duration_ms": track["duration_ms"],
            "thumbnail": (track["album"]["images"][0]["url"] if track["album"]["images"] else None),
            "url": track["external_urls"]["spotify"],
        }
        for track in tracks
    ]
