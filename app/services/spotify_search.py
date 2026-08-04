import concurrent.futures
import itertools
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


_LASTFM_TAGS = ["house", "techno"]


def _get_lastfm_chart_tracks(limit: int) -> list[dict]:
    """Puxa o 'em alta' de verdade via Last.fm (tag.getTopTracks) e resolve
    cada faixa de volta pro Spotify via busca normal — atualiza sozinho,
    sem lista fixa de artista."""
    from app.services import lastfm_service

    sp = get_client()
    per_tag = max(5, limit // len(_LASTFM_TAGS) + 5)

    def _fetch_tag(tag: str) -> list[dict]:
        try:
            return lastfm_service.get_top_tracks_for_tag(tag, limit=per_tag)
        except Exception:  # noqa: BLE001
            log.exception("falha ao buscar tag %s no Last.fm", tag)
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(_LASTFM_TAGS)) as executor:
        by_tag = list(executor.map(_fetch_tag, _LASTFM_TAGS))

    def _resolve(entry: dict) -> dict | None:
        results = sp.search(q=f"track:{entry['title']} artist:{entry['artist']}", type="track", limit=1)
        items = results.get("tracks", {}).get("items", [])
        return items[0] if items else None

    interleaved = [e for pair in itertools.zip_longest(*by_tag) for e in pair if e is not None]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        resolved = list(executor.map(_resolve, interleaved))

    by_id: dict[str, dict] = {}
    for t in resolved:
        if t is not None:
            by_id[t["id"]] = t

    return [_parse_track(t) for t in list(by_id.values())[:limit]]


# fallback final se o Last.fm nao estiver configurado/falhar: busca direto
# por artistas atuais de destaque em house/techno. Nao e "automatico" de
# verdade (lista escrita a mao), mas garante que sempre aparece algo
# reconhecivel mesmo sem chave do Last.fm configurada.
_ELECTRONIC_ARTISTS = [
    "Cloonee",
    "Solomun",
    "Prospa",
    "Interplanetary Criminal",
    "Fisher",
    "John Summit",
    "Dom Dolla",
    "CamelPhat",
    "Chris Lake",
    "Charlotte de Witte",
    "Amelie Lens",
    "Overmono",
]


def _get_genre_chart_tracks(limit: int) -> list[dict]:
    sp = get_client()

    def _search_artist(artist: str) -> list[dict]:
        try:
            results = sp.search(q=f'artist:"{artist}"', type="track", limit=3)
            return results.get("tracks", {}).get("items", [])
        except Exception:  # noqa: BLE001
            log.exception("falha ao buscar artista %s", artist)
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(_ELECTRONIC_ARTISTS)) as executor:
        results = list(executor.map(_search_artist, _ELECTRONIC_ARTISTS))

    by_id: dict[str, dict] = {}
    # intercala (1a faixa de cada artista, depois a 2a, etc) em vez de
    # empilhar tudo de um artista antes do proximo
    for tracks in itertools.zip_longest(*results):
        for t in tracks:
            if t is not None:
                by_id[t["id"]] = t

    return [_parse_track(t) for t in list(by_id.values())[:limit]]


def get_trending_tracks(limit: int = 10) -> list[dict]:
    """Sugestoes 'em alta essa semana', nessa ordem de prioridade:

    1. Playlist real do Spotify (SPOTIFY_TRENDING_PLAYLIST_ID), so funciona
       logado (/auth/login).
    2. Last.fm (tag.getTopTracks pra "house"/"techno") — automatico de
       verdade, baseado em audicao real, atualiza sozinho a cada
       carregamento. Precisa de LASTFM_API_KEY no .env.
    3. Fallback fixo: busca por artistas atuais de destaque em house/techno
       (ver _ELECTRONIC_ARTISTS), caso o Last.fm nao esteja configurado.
    """
    try:
        playlist_tracks = _get_playlist_tracks(limit)
        if playlist_tracks:
            return playlist_tracks
    except Exception:  # noqa: BLE001
        log.exception("falha ao puxar playlist %s, tentando Last.fm", TRENDING_PLAYLIST_ID)

    try:
        lastfm_tracks = _get_lastfm_chart_tracks(limit)
        if lastfm_tracks:
            return lastfm_tracks
    except Exception:  # noqa: BLE001
        log.exception("falha ao puxar chart do Last.fm, caindo pro fallback fixo")

    return _get_genre_chart_tracks(limit)
