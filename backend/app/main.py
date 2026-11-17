import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from app.core.config import settings

if settings.offline:  # guarantee no network calls to the HF hub at runtime
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from app.api.routes import ApiError, router  # noqa: E402
from app.database.db import init_db  # noqa: E402
from app.services.detection.detectors import registry  # noqa: E402
from app.services.face_analysis.faces import face_detector  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    for f in settings.tmp_dir.glob("*"):
        f.unlink(missing_ok=True)
    if os.environ.get("TRUTHLENS_SKIP_MODELS") != "1":
        registry.load_all()
    face_detector.load()
    yield


app = FastAPI(title="Detective AI", version="1.0.0", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","), allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


@app.exception_handler(ApiError)
async def api_error(request: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status, content={"detail": exc.detail, "code": exc.code, "params": exc.params})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logging.getLogger("truthlens").exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": "Internal server error.", "code": "internal"})


app.include_router(router)

# Serve the built frontend (single-process demo mode) if present.
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path == "api" or path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not found.", "code": "notFound"})
        f = (DIST / path).resolve()
        if path and f.is_file() and DIST in f.parents:
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
