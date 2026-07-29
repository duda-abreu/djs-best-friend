"""Estimativa de BPM (batidas por minuto).

O endpoint audio-features do Spotify (que antes dava BPM pronto) foi
restringido pela Spotify pra apps novos, entao aqui o BPM e calculado
localmente com deteccao de batida (librosa) em cima de um clipe de audio
curto e legitimo: o preview oficial de 30s do Spotify, ou o arquivo ja
baixado (YouTube/Spotify) apos o download.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional

import librosa
import requests

_cache: dict[str, float] = {}


def _beat_track(y, sr) -> float:
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return round(float(tempo), 1)


def estimate_from_url(cache_key: str, audio_url: str) -> Optional[float]:
    if cache_key in _cache:
        return _cache[cache_key]

    resp = requests.get(audio_url, timeout=15)
    resp.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(resp.content)
        tmp_path = tmp.name

    try:
        y, sr = librosa.load(tmp_path, sr=22050, mono=True)
        bpm = _beat_track(y, sr)
        _cache[cache_key] = bpm
        return bpm
    finally:
        os.remove(tmp_path)


def estimate_from_file(cache_key: str, file_path: Path) -> Optional[float]:
    if cache_key in _cache:
        return _cache[cache_key]

    y, sr = librosa.load(str(file_path), sr=22050, mono=True)
    bpm = _beat_track(y, sr)
    _cache[cache_key] = bpm
    return bpm
