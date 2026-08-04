from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.services import spotify_auth

router = APIRouter(tags=["auth"])


@router.get("/auth/login")
def login():
    auth_manager = spotify_auth.get_auth_manager()
    return RedirectResponse(auth_manager.get_authorize_url())


@router.get("/callback")
def callback(code: str = Query(default=""), error: str = Query(default="")):
    if error:
        raise HTTPException(400, f"login com spotify falhou: {error}")
    auth_manager = spotify_auth.get_auth_manager()
    auth_manager.get_access_token(code, check_cache=False)

    # bug do spotipy: o token do fluxo PKCE nunca grava "scope", mas a
    # validacao (validate_token) exige esse campo pra aceitar o token —
    # sem isso, is_authenticated() e qualquer chamada autenticada falham
    # pra sempre, mesmo com o token valido. Corrige gravando de volta.
    token = auth_manager.cache_handler.get_cached_token()
    if token is not None and "scope" not in token:
        token["scope"] = auth_manager.scope or ""
        auth_manager.cache_handler.save_token_to_cache(token)

    return RedirectResponse("/")


@router.get("/auth/status")
def status():
    return {"authenticated": spotify_auth.is_authenticated()}
