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
import numpy as np
import requests

_cache: dict[str, float] = {}


def _correct_octave_error(bpm: float) -> float:
    """Detectores de batida frequentemente travam numa subdivisao errada do
    pulso (ex: acham a metade, o dobro, ou 2/3 do tempo real — comum em
    house/techno com hi-hat sincopado). Se o valor detectado cai fora da
    faixa tipica de musica dancante, testa multiplicar/dividir por 2 e 1.5 e
    fica com o que cair mais perto de uma faixa plausivel.
    """
    if 90 <= bpm <= 180:
        return bpm

    candidates = [bpm, bpm * 2, bpm * 1.5, bpm / 1.5, bpm / 2]
    in_range = [c for c in candidates if 90 <= c <= 180]
    if not in_range:
        return bpm
    return min(in_range, key=lambda c: abs(c - 120))


def _beat_track(y, sr) -> float:
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    # versoes recentes do librosa retornam tempo como array (ex: [128.003])
    # em vez de escalar, e float() direto quebra nesse caso
    value = np.asarray(tempo).reshape(-1)[0]
    value = _correct_octave_error(float(value))
    return round(value, 1)


def estimate_from_url(
    cache_key: str, audio_url: str, suffix: str = ".mp3", max_bytes: Optional[int] = None
) -> Optional[float]:
    """Baixa (inteiro ou so um pedaco, via max_bytes) e estima o BPM.

    max_bytes limita o download via Range request — usado pra estimar BPM sem
    baixar o audio inteiro (ex: primeiros ~800kb de um stream do YouTube, o
    suficiente pra deteccao de batida).
    """
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
    """offset>0 serve pra pular intro em musicas completas — nao usar em
    clipes curtos (ja tem so alguns segundos, pular 20s deixaria vazio)."""
    if cache_key in _cache:
        return _cache[cache_key]

    y, sr = librosa.load(str(file_path), sr=11025, mono=True, offset=offset, duration=30)
    bpm = _beat_track(y, sr)
    _cache[cache_key] = bpm
    return bpm
