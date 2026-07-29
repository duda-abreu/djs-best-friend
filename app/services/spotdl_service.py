import subprocess
import sys
from pathlib import Path


def download_track(spotify_url: str, out_dir: Path, bitrate: str = "320k") -> Path:
    """Baixa uma faixa do Spotify via spotdl (busca a melhor correspondencia no
    YouTube Music e reencoda no bitrate pedido, com metadados/capa embutidos).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(out_dir / "{title}.{output-ext}")

    cmd = [
        sys.executable,
        "-m",
        "spotdl",
        "download",
        spotify_url,
        "--output",
        outtmpl,
        "--format",
        "mp3",
        "--bitrate",
        bitrate,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"spotdl falhou (codigo {result.returncode}): {detail[-2000:]}")

    files = [f for f in out_dir.iterdir() if f.is_file()]
    if not files:
        raise RuntimeError("spotdl nao gerou nenhum arquivo")
    return files[0]
