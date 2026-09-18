from pathlib import Path
from typing import Optional

import yt_dlp


def match_video(title: str, artist: str) -> Optional[dict]:
    results = search_videos(f"{title} {artist}", limit=1)
    return results[0] if results else None


def download_clip(video_url: str, out_dir: Path, seconds: int = 20) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(out_dir / "clip.%(ext)s")

    opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "download_ranges": lambda info, ydl: [{"start_time": 0, "end_time": seconds}],
        "force_keyframes_at_cuts": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([video_url])

    files = [f for f in out_dir.iterdir() if f.is_file()]
    if not files:
        raise RuntimeError("não foi possível baixar o clipe pra estimar o bpm")
    return files[0]


def search_videos(query: str, limit: int = 10) -> list[dict]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)

    entries = info.get("entries", []) if info else []
    return [
        {
            "source": "youtube",
            "id": entry["id"],
            "title": entry.get("title", "sem título"),
            "artist": entry.get("uploader", ""),
            "album": "",
            "duration_ms": (entry.get("duration") or 0) * 1000,
            "thumbnail": entry.get("thumbnails", [{}])[-1].get("url") if entry.get("thumbnails") else None,
            "url": f"https://www.youtube.com/watch?v={entry['id']}",
        }
        for entry in entries
        if entry
    ]


def download_audio(video_url: str, out_dir: Path, quality: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(out_dir / "%(title)s.%(ext)s")

    opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
    }

    if quality == "mp3_320":
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }
        ]

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([video_url])

    files = [f for f in out_dir.iterdir() if f.is_file()]
    if not files:
        raise RuntimeError("download do YouTube não gerou nenhum arquivo")
    return files[0]
