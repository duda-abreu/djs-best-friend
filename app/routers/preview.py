import logging
import shutil
import uuid

from fastapi import APIRouter, HTTPException, Query

from app.config import DOWNLOAD_DIR
from app.services import bpm_service, history_service, spotify_search, youtube_service

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["preview"])


@router.get("/bpm")
def bpm(key: str = Query(...), preview_url: str = Query(...)):
    try:
        value = bpm_service.estimate_from_url(key, preview_url)
        return {"bpm": value}
    except Exception as exc:  # noqa: BLE001
        log.exception("falha ao estimar bpm (preview_url) key=%s", key)
        raise HTTPException(500, f"não foi possível estimar o bpm: {exc}") from exc


@router.get("/bpm-spotify")
def bpm_spotify(track_id: str = Query(...)):
    try:
        value = spotify_search.get_audio_features_bpm(track_id)
        return {"bpm": value}
    except Exception as exc:  # noqa: BLE001
        log.exception("falha ao pegar audio-features track_id=%s", track_id)
        raise HTTPException(500, f"não foi possível pegar o bpm oficial: {exc}") from exc


@router.get("/bpm-youtube")
def bpm_youtube(key: str = Query(...), video_url: str = Query(...)):
    tmp_dir = DOWNLOAD_DIR / f"_bpm_{uuid.uuid4().hex[:8]}"
    try:
        clip_path = youtube_service.download_clip(video_url, tmp_dir, seconds=10)
        value = bpm_service.estimate_from_file(key, clip_path)
        return {"bpm": value}
    except Exception as exc:  # noqa: BLE001
        log.exception("falha ao estimar bpm (youtube) key=%s video_url=%s", key, video_url)
        raise HTTPException(500, f"não foi possível estimar o bpm: {exc}") from exc
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.get("/match")
def match(title: str = Query(...), artist: str = Query(...)):
    video = youtube_service.match_video(title, artist)
    if video is None:
        log.warning("nenhum vídeo encontrado pra prévia: title=%s artist=%s", title, artist)
        raise HTTPException(404, "nenhum vídeo encontrado pra prévia")
    return video


@router.get("/trending")
def trending(limit: int = Query(default=10, ge=1, le=50)):
    try:
        return spotify_search.get_trending_tracks(limit=limit)
    except RuntimeError as exc:
        raise HTTPException(500, str(exc)) from exc


@router.get("/history")
def history():
    return history_service.get_stats()


@router.delete("/history/{entry_id}")
def delete_history_entry(entry_id: str):
    removed = history_service.delete_entry(entry_id)
    if not removed:
        raise HTTPException(404, "entrada não encontrada")
    return {"removed": True}
