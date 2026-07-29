import logging

import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

log = logging.getLogger(__name__)

from app.config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    TRENDING_GENRE_ID,
    TRENDING_PLAYLIST_ID,
    TRENDING_STOREFRONT,
)

# feed de charts da Apple filtrado por genero (7 = Dance/Eletronica)
_APPLE_CHARTS_URL = "https://itunes.apple.com/{storefront}/rss/topsongs/limit={limit}/genre={genre}/json"

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


def _parse_track(track: dict) -> dict:
    return {
        "source": "spotify",
        "id": track["id"],
        "title": track["name"],
        "artist": ", ".join(a["name"] for a in track["artists"]),
        "album": track["album"]["name"],
        "duration_ms": track["duration_ms"],
        "thumbnail": (track["album"]["images"][0]["url"] if track["album"]["images"] else None),
        "url": track["external_urls"]["spotify"],
        "preview_url": track.get("preview_url"),
    }


# a Spotify passou a rejeitar (400 "Invalid limit") qualquer valor de limit
# de busca acima de 10 nesse app — pra pedidos maiores, pagina com varias
# chamadas de 10 e concatena
_SEARCH_PAGE_SIZE = 10


def search_tracks(query: str, limit: int = 10) -> list[dict]:
    sp = get_client()
    tracks: list[dict] = []
    offset = 0
    while len(tracks) < limit:
        page_size = min(_SEARCH_PAGE_SIZE, limit - len(tracks))
        results = sp.search(q=query, type="track", limit=page_size, offset=offset)
        items = results.get("tracks", {}).get("items", [])
        tracks.extend(items)
        if len(items) < page_size:
            break
        offset += page_size
    return [_parse_track(t) for t in tracks[:limit]]


def get_audio_features_bpm(track_id: str) -> float | None:
    """BPM oficial via /v1/audio-features. So funciona com um usuario
    autenticado de verdade (login com Spotify) — Client Credentials leva 403."""
    from app.services import spotify_auth

    sp = spotify_auth.get_authenticated_client()
    features = sp.audio_features([track_id])
    if not features or not features[0]:
        return None
    return round(features[0]["tempo"], 1)


def _get_playlist_tracks(limit: int) -> list[dict]:
    """Tenta puxar a playlist configurada (SPOTIFY_TRENDING_PLAYLIST_ID) ao
    vivo — so funciona se o usuario estiver logado com Spotify de verdade
    (Client Credentials leva 403/404 em qualquer playlist, testado)."""
    from app.services import spotify_auth

    if not TRENDING_PLAYLIST_ID or not spotify_auth.is_authenticated():
        return []

    sp = spotify_auth.get_authenticated_client()
    results = sp.playlist_items(
        TRENDING_PLAYLIST_ID,
        limit=min(limit, 100),
        fields="items.track(id,name,artists,album,duration_ms,external_urls,preview_url)",
        additional_types=["track"],
    )
    items = results.get("items", [])
    return [_parse_track(i["track"]) for i in items if i.get("track")]


def get_trending_tracks(limit: int = 10) -> list[dict]:
    """Sugestoes 'em alta essa semana'.

    Se SPOTIFY_TRENDING_PLAYLIST_ID estiver configurado e o usuario logado
    com Spotify (/auth/login), tenta puxar essa playlist ao vivo — assim ela
    acompanha as mudancas da playlist de verdade. Caso contrario (ou se
    falhar), cai pro grafico publico "mais tocadas" da Apple Music (sem
    chave, sem login), resolvendo cada faixa de volta pro Spotify via busca
    normal pra manter o mesmo formato de item usado no resto do site.
    """
    try:
        playlist_tracks = _get_playlist_tracks(limit)
        if playlist_tracks:
            return playlist_tracks
    except Exception:  # noqa: BLE001
        log.exception("falha ao puxar playlist %s, caindo pro grafico da Apple", TRENDING_PLAYLIST_ID)

    resp = requests.get(
        _APPLE_CHARTS_URL.format(storefront=TRENDING_STOREFRONT, limit=limit, genre=TRENDING_GENRE_ID),
        timeout=10,
    )
    resp.raise_for_status()
    chart = resp.json().get("feed", {}).get("entry", [])

    sp = get_client()
    tracks = []
    for entry in chart:
        name = entry["im:name"]["label"]
        artist = entry["im:artist"]["label"]
        results = sp.search(q=f"{name} {artist}", type="track", limit=1)
        items = results.get("tracks", {}).get("items", [])
        if items:
            tracks.append(_parse_track(items[0]))
    return tracks
