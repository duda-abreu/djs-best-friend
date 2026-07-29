import hmac
import time
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import BASIC_AUTH_PASSWORD, BASIC_AUTH_USER, BASE_DIR, RATE_LIMIT_PER_MINUTE
from app.logging_config import setup_logging
from app.routers import auth, download, preview, search
from app.services import jobs

setup_logging()

app = FastAPI(title="djs-best-friend")

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

app.include_router(search.router)
app.include_router(download.router)
app.include_router(preview.router)
app.include_router(auth.router)

_hits: dict[str, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/download") and request.method == "POST":
            ip = request.client.host if request.client else "unknown"
            now = time.time()
            recent = [t for t in _hits[ip] if now - t < 60]
            if len(recent) >= RATE_LIMIT_PER_MINUTE:
                return JSONResponse(
                    {"detail": "limite de downloads por minuto atingido, tente novamente em instantes"},
                    status_code=429,
                )
            recent.append(now)
            _hits[ip] = recent
        return await call_next(request)


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """So entra em acao se BASIC_AUTH_USER/BASIC_AUTH_PASSWORD estiverem
    configurados (pensado pra quando o site estiver hospedado publicamente,
    nao pra uso local)."""

    async def dispatch(self, request: Request, call_next):
        if not BASIC_AUTH_USER or not BASIC_AUTH_PASSWORD:
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if auth.startswith("Basic "):
            import base64

            try:
                user, password = base64.b64decode(auth[6:]).decode().split(":", 1)
            except Exception:  # noqa: BLE001
                user, password = "", ""
            if hmac.compare_digest(user, BASIC_AUTH_USER) and hmac.compare_digest(password, BASIC_AUTH_PASSWORD):
                return await call_next(request)

        return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="djs-best-friend"'})


app.add_middleware(RateLimitMiddleware)
app.add_middleware(BasicAuthMiddleware)


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.on_event("startup")
def _startup_cleanup():
    jobs.cleanup_expired()
