"""Gera docs/trending.json com o "Em alta essa semana" da versao online.

Le os Top 100 por genero do Beatport e liga cada faixa a iTunes Search API
(pra ter capa, previa de 30s e link). Roda toda semana pelo GitHub Actions.
"""
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services import beatport_service  # noqa: E402

OUTPUT = ROOT / "docs" / "trending.json"
TARGET = 50
MAX_ATTEMPTS = 90
DELAY_SECONDS = 3.2  # a iTunes Search API limita em ~20 chamadas por minuto

_MIX_SUFFIX_RE = re.compile(r"\s*[(\[]\s*(original|extended|radio)(\s+(mix|edit|version))?\s*[)\]]\s*$", re.I)
_COUNTRY_SUFFIX_RE = re.compile(r"\s*\([A-Z]{2}\)\s*$")
_PLAIN_MIXES = {"original mix", "extended mix", "extended", "original", "radio edit", "radio mix"}


def _search_itunes(term: str) -> list[dict]:
    for attempt in range(3):
        resp = requests.get(
            "https://itunes.apple.com/search",
            params={"term": term, "media": "music", "entity": "song", "limit": 10, "country": "BR"},
            timeout=20,
        )
        if resp.status_code in (403, 429):
            time.sleep(30 * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp.json().get("results", [])
    return []


def _match(entry: dict) -> dict | None:
    title = " ".join(_MIX_SUFFIX_RE.sub("", entry["title"]).split())
    artists = [_COUNTRY_SUFFIX_RE.sub("", a).strip().lower() for a in entry["artists"]]
    mix = entry["mix"].strip().lower()
    wants_mix = bool(mix) and mix not in _PLAIN_MIXES

    for track in _search_itunes(f"{title} {artists[0]}"):
        name = track.get("trackName", "").lower()
        artist_name = track.get("artistName", "").lower()
        if not track.get("previewUrl") or title.lower() not in name:
            continue
        if not any(a in artist_name for a in artists):
            continue
        if wants_mix and mix not in name:
            continue
        return track
    return None


def main() -> None:
    chart = beatport_service.get_top_tracks()
    if not chart:
        sys.exit("Beatport nao retornou faixas, mantendo o trending.json atual")

    tracks: list[dict] = []
    seen_ids: set[int] = set()
    for entry in chart[:MAX_ATTEMPTS]:
        if len(tracks) >= TARGET:
            break
        try:
            found = _match(entry)
        except requests.RequestException as exc:
            print(f"falha ao buscar {entry['title']}: {exc}")
            found = None
        time.sleep(DELAY_SECONDS)
        if found is None or found["trackId"] in seen_ids:
            continue
        seen_ids.add(found["trackId"])
        tracks.append(
            {
                "trackName": found["trackName"],
                "artistName": found["artistName"],
                "collectionName": found.get("collectionName", ""),
                "artworkUrl100": found.get("artworkUrl100", ""),
                "previewUrl": found["previewUrl"],
                "trackViewUrl": found.get("trackViewUrl", ""),
                "trackTimeMillis": found.get("trackTimeMillis", 0),
                "bpm": entry["bpm"],
            }
        )

    if len(tracks) < 10:
        sys.exit(f"so {len(tracks)} faixas achadas, mantendo o trending.json atual")

    OUTPUT.write_text(
        json.dumps(
            {"updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "tracks": tracks},
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{len(tracks)} faixas salvas em {OUTPUT}")


if __name__ == "__main__":
    main()
