import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")

DOWNLOAD_DIR = BASE_DIR / os.getenv("DOWNLOAD_DIR", "downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "6"))
FILE_TTL_SECONDS = int(os.getenv("FILE_TTL_SECONDS", "1800"))
