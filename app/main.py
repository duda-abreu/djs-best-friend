import time
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import BASE_DIR, RATE_LIMIT_PER_MINUTE
from app.routers import download, preview, search
from app.services import jobs

app = FastAPI(title="djs-best-friend")

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

app.include_router(search.router)
app.include_router(download.router)
app.include_router(preview.router)

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


app.add_middleware(RateLimitMiddleware)


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.on_event("startup")
def _startup_cleanup():
    jobs.cleanup_expired()
