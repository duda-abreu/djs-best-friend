import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests

log = logging.getLogger(__name__)

_BASE_URL = "https://www.beatport.com"

_GENRE_CHARTS = [
    "/genre/house/5/top-100",
    "/genre/tech-house/11/top-100",
    "/genre/techno-peak-time-driving/6/top-100",
    "/genre/melodic-house-techno/90/top-100",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

_NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
_CACHE_TTL_SECONDS = 3600

_cache: dict = {"at": 0.0, "tracks": []}


def _fetch_chart(path: str) -> list[dict]:
    resp = requests.get(_BASE_URL + path, headers=_HEADERS, timeout=20)
    resp.raise_for_status()
    match = _NEXT_DATA_RE.search(resp.text)
    if not match:
        raise RuntimeError(f"Beatport: __NEXT_DATA__ não encontrado em {path}")

    queries = json.loads(match.group(1))["props"]["pageProps"]["dehydratedState"]["queries"]
    for query in queries:
        data = query.get("state", {}).get("data")
        if isinstance(data, dict) and isinstance(data.get("results"), list):
            return [
                {
                    "title": t["name"],
                    "mix": t.get("mix_name") or "",
                    "artists": [a["name"] for a in t.get("artists", [])],
                    "bpm": t.get("bpm"),
                }
                for t in data["results"]
                if t.get("name") and t.get("artists")
            ]
    raise RuntimeError(f"Beatport: lista de faixas não encontrada em {path}")


def _safe_fetch_chart(path: str) -> list[dict]:
    try:
        return _fetch_chart(path)
    except Exception:  # noqa: BLE001
        log.exception("falha ao buscar chart do Beatport %s", path)
        return []


def get_top_tracks() -> list[dict]:
    """Top 100 dos generos de house/techno do Beatport, intercalados por posicao.

    Cacheado por 1h pra nao bater no site a cada carregamento.
    """
    if _cache["tracks"] and time.time() - _cache["at"] < _CACHE_TTL_SECONDS:
        return _cache["tracks"]

    with ThreadPoolExecutor(max_workers=len(_GENRE_CHARTS)) as executor:
        charts = list(executor.map(_safe_fetch_chart, _GENRE_CHARTS))

    tracks: list[dict] = []
    seen: set[tuple[str, str]] = set()
    longest = max((len(c) for c in charts), default=0)
    for rank in range(longest):
        for chart in charts:
            if rank >= len(chart):
                continue
            track = chart[rank]
            key = (track["title"].lower(), track["artists"][0].lower())
            if key not in seen:
                seen.add(key)
                tracks.append(track)

    if tracks:
        _cache.update(at=time.time(), tracks=tracks)
    return tracks
