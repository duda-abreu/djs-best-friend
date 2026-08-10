
import os
import tempfile
from pathlib import Path
from typing import Optional

import librosa
import numpy as np
import requests

_cache: dict[str, float] = {}


def _correct_octave_error(bpm: float) -> float:
    if 90 <= bpm <= 180:
        return bpm

    candidates = [bpm, bpm * 2, bpm * 1.5, bpm / 1.5, bpm / 2]
    in_range = [c for c in candidates if 90 <= c <= 180]
    if not in_range:
        return bpm
    return min(in_range, key=lambda c: abs(c - 120))


def _beat_track(y, sr) -> float:
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    value = np.asarray(tempo).reshape(-1)[0]
    value = _correct_octave_error(float(value))
    return round(value, 1)


def estimate_from_url(
    cache_key: str, audio_url: str, suffix: str = ".mp3", max_bytes: Optional[int] = None
) -> Optional[float]:
    if cache_key in _cache:
        return _cache[cache_key]

    headers = {"Range": f"bytes=0-{max_bytes}"} if max_bytes else None
    resp = requests.get(audio_url, headers=headers, timeout=15)
    resp.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(resp.content)
        tmp_path = tmp.name

    try:
        y, sr = librosa.load(tmp_path, sr=11025, mono=True, duration=30)
        bpm = _beat_track(y, sr)
        _cache[cache_key] = bpm
        return bpm
    finally:
        os.remove(tmp_path)


def estimate_from_file(cache_key: str, file_path: Path, offset: float = 0) -> Optional[float]:
    if cache_key in _cache:
        return _cache[cache_key]

    y, sr = librosa.load(str(file_path), sr=11025, mono=True, offset=offset, duration=30)
    bpm = _beat_track(y, sr)
    _cache[cache_key] = bpm
    return bpm
