import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from app.config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    TRENDING_GENRE_ID,
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


def get_trending_tracks(limit: int = 10) -> list[dict]:
    """Sugestoes 'em alta essa semana'.

    O endpoint de playlists/browse do Spotify (inclusive as playlists
    editoriais deles, tipo a "mint") retorna 403/404 pra apps em Client
    Credentials (sem login de usuario) — a Spotify restringiu esse acesso
    em 2024. Por isso o grafico de "mais tocadas" vem do feed publico da
    Apple Music (sem chave, sem login), e cada faixa e resolvida de volta
    pro Spotify via busca normal (que essa continua funcionando), pra manter
    o mesmo formato de item (com preview_url, id, etc) que o resto do site usa.
    """
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
