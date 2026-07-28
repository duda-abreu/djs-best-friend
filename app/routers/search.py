from fastapi import APIRouter, HTTPException, Query

from app.services import spotify_search, youtube_service

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def search(q: str = Query(min_length=1), source: str = Query(default="spotify")):
    try:
        if source == "spotify":
            return spotify_search.search_tracks(q)
        elif source == "youtube":
            return youtube_service.search_videos(q)
        raise HTTPException(400, f"fonte invalida: {source}")
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc
