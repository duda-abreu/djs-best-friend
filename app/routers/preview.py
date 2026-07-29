from fastapi import APIRouter, HTTPException, Query

from app.services import bpm_service, history_service, spotify_search, youtube_service

router = APIRouter(prefix="/api", tags=["preview"])


@router.get("/bpm")
def bpm(key: str = Query(...), preview_url: str = Query(...)):
    try:
        value = bpm_service.estimate_from_url(key, preview_url)
        return {"bpm": value}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"nao foi possivel estimar o bpm: {exc}") from exc


@router.get("/match")
def match(title: str = Query(...), artist: str = Query(...)):
    """Acha um video do YouTube pra usar como preview quando o Spotify nao
    fornece preview_url pra uma faixa (comum em apps novos)."""
    video = youtube_service.match_video(title, artist)
    if video is None:
        raise HTTPException(404, "nenhum video encontrado pra preview")
    return video


@router.get("/trending")
def trending():
    try:
        return spotify_search.get_trending_tracks()
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc


@router.get("/history")
def history():
    return history_service.get_stats()
