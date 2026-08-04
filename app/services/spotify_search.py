import concurrent.futures
import logging

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

log = logging.getLogger(__name__)

from app.config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, TRENDING_PLAYLIST_ID

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

    if not TRENDING_PLAYLIST_ID:
        log.info("playlist trending nao configurada (SPOTIFY_TRENDING_PLAYLIST_ID vazio)")
        return []
    if not spotify_auth.is_authenticated():
        log.info("playlist trending configurada (%s) mas usuario nao esta logado", TRENDING_PLAYLIST_ID)
        return []

    log.info("tentando puxar playlist %s (usuario logado)", TRENDING_PLAYLIST_ID)
    sp = spotify_auth.get_authenticated_client()
    results = sp.playlist_items(
        TRENDING_PLAYLIST_ID,
        limit=min(limit, 100),
        fields="items.track(id,name,artists,album,duration_ms,external_urls,preview_url)",
        additional_types=["track"],
    )
    items = results.get("items", [])
    parsed = [_parse_track(i["track"]) for i in items if i.get("track")]
    log.info("playlist %s retornou %d faixas", TRENDING_PLAYLIST_ID, len(parsed))
    return parsed


# subgeneros usados pra montar o "em alta" quando nao tem playlist logada —
# a Spotify marca cada faixa com genero real (tag "genre:" na busca), o que
# da resultado bem mais preciso que um chart generico "eletronica" da Apple
# (testado: aquele chart inclui gospel, hip-hop etc que a Apple tambem rotula
# como "Eletronica" no catalogo dela)
_ELECTRONIC_GENRES = [
    "house",
    "techno",
    "edm",
    "melodic house",
    "tech house",
    "trance",
    "drum and bass",
]


def _get_genre_chart_tracks(limit: int) -> list[dict]:
    sp = get_client()

    def _search_genre(genre: str) -> list[dict]:
        try:
            results = sp.search(q=f'genre:"{genre}"', type="track", limit=10)
            return results.get("tracks", {}).get("items", [])
        except Exception:  # noqa: BLE001
            log.exception("falha ao buscar genero %s", genre)
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(_ELECTRONIC_GENRES)) as executor:
        results = executor.map(_search_genre, _ELECTRONIC_GENRES)

    by_id: dict[str, dict] = {}
    for tracks in results:
        for t in tracks:
            by_id[t["id"]] = t

    ranked = sorted(by_id.values(), key=lambda t: t.get("popularity", 0), reverse=True)
    return [_parse_track(t) for t in ranked[:limit]]


def get_trending_tracks(limit: int = 10) -> list[dict]:
    """Sugestoes 'em alta essa semana'.

    Se SPOTIFY_TRENDING_PLAYLIST_ID estiver configurado e o usuario logado
    com Spotify (/auth/login), tenta puxar essa playlist ao vivo — assim ela
    acompanha as mudancas da playlist de verdade. Caso contrario (ou se
    falhar), monta a lista combinando buscas por subgenero eletronico
    (house, techno, edm, etc) ordenadas por popularidade — atualiza sozinho
    a cada carregamento, sem cache.
    """
    try:
        playlist_tracks = _get_playlist_tracks(limit)
        if playlist_tracks:
            return playlist_tracks
    except Exception:  # noqa: BLE001
        log.exception("falha ao puxar playlist %s, caindo pra busca por genero", TRENDING_PLAYLIST_ID)

    return _get_genre_chart_tracks(limit)
