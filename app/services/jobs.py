import concurrent.futures
import logging
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.config import DOWNLOAD_DIR, FILE_TTL_SECONDS
from app.services import bpm_service, history_service, spotdl_service, youtube_service

log = logging.getLogger(__name__)

DOWNLOAD_TIMEOUT_SECONDS = 240
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


@dataclass
class Job:
    id: str
    source: str
    title: str = ""
    artist: str = ""
    status: str = "pending"  # pending -> downloading -> done -> error
    file_path: Optional[Path] = None
    bpm: Optional[float] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)


_jobs: dict[str, Job] = {}


def create_job(source: str, title: str, artist: str) -> Job:
    job = Job(id=uuid.uuid4().hex[:12], source=source, title=title, artist=artist)
    _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)


def run_job(job_id: str, source: str, ref: str, quality: str) -> None:
    job = _jobs[job_id]
    job.status = "downloading"
    job_dir = DOWNLOAD_DIR / job_id
    log.info("job %s: iniciando download (source=%s, ref=%s, quality=%s)", job_id, source, ref, quality)
    try:
        if source == "spotify":
            task = _executor.submit(spotdl_service.download_track, ref, job_dir, quality)
        elif source == "youtube":
            task = _executor.submit(youtube_service.download_audio, ref, job_dir, quality)
        else:
            raise ValueError(f"fonte desconhecida: {source}")

        try:
            file_path = task.result(timeout=DOWNLOAD_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError as exc:
            log.error("job %s: timeout depois de %ss", job_id, DOWNLOAD_TIMEOUT_SECONDS)
            raise RuntimeError(
                "download demorou demais e foi cancelado — confira se o ffmpeg "
                "está instalado e no PATH (feche e reabra o terminal depois de instalar)"
            ) from exc

        job.file_path = file_path
        job.status = "done"
        log.info("job %s: download concluido em %s", job_id, file_path)

        try:
            job.bpm = bpm_service.estimate_from_file(job.id, file_path, offset=20)
        except Exception:  # noqa: BLE001
            log.exception("job %s: falha ao calcular bpm do arquivo baixado", job_id)
            job.bpm = None

        history_service.add_entry(
            entry_id=job.id,
            title=job.title,
            artist=job.artist,
            source=source,
            quality=quality,
            size_bytes=file_path.stat().st_size,
            bpm=job.bpm,
            file_path=str(file_path),
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("job %s: falhou", job_id)
        job.status = "error"
        job.error = str(exc)


def cleanup_expired() -> None:
    now = time.time()
    expired = [j for j in _jobs.values() if now - j.created_at > FILE_TTL_SECONDS]
    for job in expired:
        job_dir = DOWNLOAD_DIR / job.id
        shutil.rmtree(job_dir, ignore_errors=True)
        _jobs.pop(job.id, None)
