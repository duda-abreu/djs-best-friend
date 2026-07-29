import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
# precisa bater exatamente com um Redirect URI cadastrado no app do Spotify
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/callback")
SPOTIFY_TOKEN_CACHE = BASE_DIR / ".spotify_user_token.json"

# pais/genero usados pra pegar o grafico "mais tocadas" (feed publico da Apple,
# sem precisar de chave/login) que alimenta a secao "em alta essa semana".
# genero 7 = Dance/Eletronica no catalogo da Apple Music.
TRENDING_STOREFRONT = os.getenv("TRENDING_STOREFRONT", "br")
TRENDING_GENRE_ID = os.getenv("TRENDING_GENRE_ID", "7")

DOWNLOAD_DIR = BASE_DIR / os.getenv("DOWNLOAD_DIR", "downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "6"))
FILE_TTL_SECONDS = int(os.getenv("FILE_TTL_SECONDS", "1800"))

# se configurados, exige login HTTP Basic pra acessar o site — pensado pra
# quando ele estiver hospedado publicamente (ex: Railway), nao pra uso local
BASIC_AUTH_USER = os.getenv("BASIC_AUTH_USER", "")
BASIC_AUTH_PASSWORD = os.getenv("BASIC_AUTH_PASSWORD", "")
