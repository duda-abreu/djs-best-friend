import json
import threading
import time
from pathlib import Path
from typing import Optional

from app.config import DOWNLOAD_DIR

_HISTORY_FILE = DOWNLOAD_DIR / "history.json"
_lock = threading.Lock()


def _load() -> list[dict]:
    if not _HISTORY_FILE.exists():
        return []
    with open(_HISTORY_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save(entries: list[dict]) -> None:
    with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def add_entry(
    title: str,
    artist: str,
    source: str,
    quality: str,
    size_bytes: int,
    bpm: Optional[float],
) -> None:
    with _lock:
        entries = _load()
        entries.append(
            {
                "title": title,
                "artist": artist,
                "source": source,
                "quality": quality,
                "size_bytes": size_bytes,
                "bpm": bpm,
                "downloaded_at": time.time(),
            }
        )
        _save(entries)


def get_stats() -> dict:
    with _lock:
        entries = _load()

    total_bytes = sum(e["size_bytes"] for e in entries)
    week_ago = time.time() - 7 * 24 * 3600
    recent = sorted(
        [e for e in entries if e["downloaded_at"] >= week_ago],
        key=lambda e: e["downloaded_at"],
        reverse=True,
    )

    return {
        "total_songs": len(entries),
        "total_gb": round(total_bytes / (1024 ** 3), 3),
        "recent_week": recent,
    }
