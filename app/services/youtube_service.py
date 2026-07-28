from pathlib import Path

import yt_dlp


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
            "title": entry.get("title", "Sem titulo"),
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
    """Baixa audio de um video do YouTube.

    quality="original": mantem o melhor stream de audio disponivel sem reencodar
    (evita "upscale" falso de bitrate).
    quality="mp3_320": reencoda para mp3 320kbps (util por compatibilidade,
    nao aumenta a qualidade real acima do stream original).
    """
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
        raise RuntimeError("Download do YouTube nao gerou nenhum arquivo")
    return files[0]
