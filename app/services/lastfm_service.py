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


# tags de genero especificas o suficiente pra nao dar falso positivo com pop
# mainstream — "electronic"/"dance"/"electro" sozinhas foram tentadas antes e
# deram match com Madonna, Lady Gaga, KATSEYE etc (que tem producao
# eletronica mas nao sao house/techno). "house"/"techno" como substring nao
# da falso positivo em nada comum (diferente de "electro", que bate em
# "electropop").
_ELECTRONIC_TAG_KEYWORDS = [
    "house", "techno", "trance", "dubstep", "drum and bass", "dnb", "idm", "downtempo", "edm",
]

# so olha as top 3 tags (as mais relevantes) — um artista house/techno de
# verdade tem isso logo no topo, nao enterrado na 5a/6a tag
_TOP_N_TAGS = 3


def artist_is_electronic(artist: str) -> bool:
    """Checa as tags de genero do ARTISTA (nao da faixa) no Last.fm — mais
    confiavel que tag.gettoptracks pra filtrar ruido tipo k-pop/pop marcado
    incorretamente como house/techno."""
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
