from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services import jobs

router = APIRouter(prefix="/api/download", tags=["download"])


class DownloadRequest(BaseModel):
    source: str  # "spotify" | "youtube"
    ref: str  # url da faixa/video
    quality: str = "320k"  # "320k" (spotify) ou "original" / "mp3_320" (youtube)
    title: str = ""
    artist: str = ""


@router.post("")
def start_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    if req.source not in ("spotify", "youtube"):
        raise HTTPException(400, f"fonte invalida: {req.source}")

    job = jobs.create_job(req.source, req.title, req.artist)
    background_tasks.add_task(jobs.run_job, job.id, req.source, req.ref, req.quality)
    return {"job_id": job.id, "status": job.status}


@router.get("/{job_id}/status")
def download_status(job_id: str):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(404, "job nao encontrado")
    return {"job_id": job.id, "status": job.status, "error": job.error, "bpm": job.bpm}


@router.get("/{job_id}/file")
def download_file(job_id: str):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(404, "job nao encontrado")
    if job.status != "done" or job.file_path is None:
        raise HTTPException(409, f"job ainda nao concluido (status={job.status})")
    return FileResponse(job.file_path, filename=job.file_path.name)
