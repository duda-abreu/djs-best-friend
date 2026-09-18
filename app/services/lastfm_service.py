
import logging

import requests

from app.config import LASTFM_API_KEY

log = logging.getLogger(__name__)

_API_URL = "https://ws.audioscrobbler.com/2.0/"


def get_top_tracks_for_tag(tag: str, limit: int = 20) -> list[dict]:
    if not LASTFM_API_KEY:
        raise RuntimeError("LASTFM_API_KEY não configurada no .env")

    resp = requests.get(
        _API_URL,
        params={
            "method": "tag.gettoptracks",
            "tag": tag,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "limit": limit,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise RuntimeError(f"Last.fm erro {data['error']}: {data.get('message')}")

    tracks = data.get("tracks", {}).get("track", [])
    return [
        {"title": t["name"], "artist": t["artist"]["name"]}
        for t in tracks
        if t.get("name") and t.get("artist", {}).get("name")
    ]


_ELECTRONIC_TAG_KEYWORDS = [
    "house", "techno", "trance", "dubstep", "drum and bass", "dnb", "idm", "downtempo", "edm",
]

_TOP_N_TAGS = 3


def artist_is_electronic(artist: str) -> bool:
    if not LASTFM_API_KEY:
        return False
    try:
        resp = requests.get(
            _API_URL,
            params={
                "method": "artist.gettoptags",
                "artist": artist,
                "api_key": LASTFM_API_KEY,
                "format": "json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        tags = [t["name"].lower() for t in data.get("toptags", {}).get("tag", [])[:_TOP_N_TAGS]]
        return any(any(kw in tag for kw in _ELECTRONIC_TAG_KEYWORDS) for tag in tags)
    except Exception:  # noqa: BLE001
        log.exception("falha ao checar tags do artista %s no Last.fm", artist)
        return False
