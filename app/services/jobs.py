import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.config import DOWNLOAD_DIR, FILE_TTL_SECONDS
from app.services import spotdl_service, youtube_service


@dataclass
class Job:
    id: str
    source: str
    status: str = "pending"  # pending -> downloading -> done -> error
    file_path: Optional[Path] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)


_jobs: dict[str, Job] = {}


def create_job(source: str) -> Job:
    job = Job(id=uuid.uuid4().hex[:12], source=source)
    _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)


def run_job(job_id: str, source: str, ref: str, quality: str) -> None:
    job = _jobs[job_id]
    job.status = "downloading"
    job_dir = DOWNLOAD_DIR / job_id
    try:
        if source == "spotify":
            file_path = spotdl_service.download_track(ref, job_dir, bitrate=quality)
        elif source == "youtube":
            file_path = youtube_service.download_audio(ref, job_dir, quality=quality)
        else:
            raise ValueError(f"fonte desconhecida: {source}")

        job.file_path = file_path
        job.status = "done"
    except Exception as exc:  # noqa: BLE001
        job.status = "error"
        job.error = str(exc)


def cleanup_expired() -> None:
    now = time.time()
    expired = [j for j in _jobs.values() if now - j.created_at > FILE_TTL_SECONDS]
    for job in expired:
        job_dir = DOWNLOAD_DIR / job.id
        shutil.rmtree(job_dir, ignore_errors=True)
        _jobs.pop(job.id, None)
