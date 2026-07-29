from fastapi import APIRouter, HTTPException, Query

from app.services import bpm_service, history_service

router = APIRouter(prefix="/api", tags=["preview"])


@router.get("/bpm")
def bpm(key: str = Query(...), preview_url: str = Query(...)):
    try:
        value = bpm_service.estimate_from_url(key, preview_url)
        return {"bpm": value}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"nao foi possivel estimar o bpm: {exc}") from exc


@router.get("/history")
def history():
    return history_service.get_stats()
