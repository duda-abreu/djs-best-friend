"""Login real do usuario com Spotify (Authorization Code + PKCE, sem client
secret) — usado so pra tentar destravar o BPM via audio-features, que a
Spotify bloqueia (403) pra apps sem usuario logado (so Client Credentials).
O login acontece na propria pagina da Spotify; este app nunca ve a senha.
"""

import spotipy
from spotipy.oauth2 import SpotifyPKCE

from app.config import SPOTIFY_CLIENT_ID, SPOTIFY_REDIRECT_URI, SPOTIFY_TOKEN_CACHE

_auth_manager: SpotifyPKCE | None = None


def get_auth_manager() -> SpotifyPKCE:
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = SpotifyPKCE(
            client_id=SPOTIFY_CLIENT_ID,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope="playlist-read-private playlist-read-collaborative",
            cache_path=str(SPOTIFY_TOKEN_CACHE),
            open_browser=False,
        )
    return _auth_manager


def is_authenticated() -> bool:
    auth_manager = get_auth_manager()
    token = auth_manager.get_cached_token()
    return bool(token)


def get_authenticated_client() -> spotipy.Spotify:
    return spotipy.Spotify(auth_manager=get_auth_manager())
