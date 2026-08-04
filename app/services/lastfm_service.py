"""Grafico 'em alta' de verdade via Last.fm (tag.getTopTracks) — atualiza
sozinho, baseado na audicao real dos usuarios do Last.fm pra uma tag/genero,
sem depender de uma lista fixa de artistas escrita a mao.
"""

import logging

import requests

from app.config import LASTFM_API_KEY

log = logging.getLogger(__name__)

_API_URL = "https://ws.audioscrobbler.com/2.0/"


def get_top_tracks_for_tag(tag: str, limit: int = 20) -> list[dict]:
    """Retorna [{'title':..., 'artist':...}, ...] pra uma tag do Last.fm
    (ex: 'house', 'techno'). Levanta RuntimeError se a chave nao estiver
    configurada."""
    if not LASTFM_API_KEY:
        raise RuntimeError("LASTFM_API_KEY nao configurada no .env")

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
