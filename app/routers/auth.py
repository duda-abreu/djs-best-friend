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
    return RedirectResponse("/")


@router.get("/auth/status")
def status():
    return {"authenticated": spotify_auth.is_authenticated()}
