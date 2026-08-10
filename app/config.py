import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/callback")
SPOTIFY_TOKEN_CACHE = BASE_DIR / ".spotify_user_token.json"

TRENDING_PLAYLIST_ID = os.getenv("SPOTIFY_TRENDING_PLAYLIST_ID", "")

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY", "")

DOWNLOAD_DIR = BASE_DIR / os.getenv("DOWNLOAD_DIR", "downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "6"))
FILE_TTL_SECONDS = int(os.getenv("FILE_TTL_SECONDS", "1800"))

BASIC_AUTH_USER = os.getenv("BASIC_AUTH_USER", "")
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "")
