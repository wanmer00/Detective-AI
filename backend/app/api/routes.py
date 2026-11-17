import importlib.util
import json
import logging
import shutil
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import UploadError
from app.i18n import norm_lang, t as tr
from app.database.db import Scan, get_db
from app.services.detection.detectors import registry
from app.services.face_analysis.faces import face_detector
from app.services.pipeline import run_analysis
from app.services.reporting.pdf import build_pdf

log = logging.getLogger("truthlens.api")
router = APIRouter(prefix="/api")
SAMPLES_DIR = Path(__file__).resolve().parents[3] / "sample_images"
VISUAL_KEYS = {"original", "saliency", "ela", "faces"}


class ApiError(Exception):
    """Error with a stable code for the UI (errors.<code> in the locale files) and an English `detail`."""

    def __init__(self, status: int, code: str, **params):
        super().__init__(code)
        self.status, self.code, self.params = status, code, params
        self.detail = tr(f"errors.{code}", **params)


def _summary(s: Scan) -> dict:
    a = s.report["assessment"]
    return {"scan_id": s.id, "filename": s.filename, "created_at": s.created_at.isoformat(), "verdict": s.verdict,
            "verdict_label": a["verdict_label"], "ai_likelihood": s.ai_likelihood, "file_type": s.file_type,
            "width": s.width, "height": s.height, "is_demo": bool(s.is_demo), "evidence_strength": a["evidence_strength"],
            "detection_confidence": (a.get("detection_confidence") or {}).get("level"),
            "thumbnail": f"/api/scans/{s.id}/image/original"}


def _store(db: Session, r: dict) -> Scan:
    s = Scan(id=r["scan_id"], filename=r["filename"], sha256=r["file"]["sha256"], file_type=r["file"]["format"],
             width=r["file"]["width"], height=r["file"]["height"], size_bytes=r["file"]["size_bytes"],
             verdict=r["assessment"]["verdict"], ai_likelihood=r["assessment"]["ai_likelihood"],
             processing_ms=r["processing_ms"], is_demo=int(r["is_demo"]), report=r)
    db.add(s)
    db.commit()
    return s


async def _analyze(db: Session, data: bytes, filename: str, demo=False) -> dict:
    try:
        r = await run_in_threadpool(run_analysis, data, filename, demo)
    except UploadError as e:
        raise ApiError(400, e.code, **e.params)
    except Exception:
        log.exception("analysis failed")
        raise ApiError(500, "analysisFailed")
    _store(db, r)
    return r


@router.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    deps = {m: importlib.util.find_spec(m) is not None for m in
            ("torch", "transformers", "cv2", "PIL", "reportlab", "c2pa")}
    deps["exiftool"] = shutil.which("exiftool") is not None
    cuda = None
    if deps["torch"]:
        import torch
        cuda = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    models = registry.status()
    ready = db_ok and registry.primary.available
    return {"status": "ready" if ready else "degraded", "backend": True, "database": db_ok,
            "models_loaded": registry.loaded, "detector_ready": registry.primary.available,
            "models": models, "face_detector": face_detector.backend, "dependencies": deps, "gpu": cuda,
            "python": sys.version.split()[0], "offline_mode": settings.offline, "max_upload_mb": settings.max_upload_mb}


@router.post("/analyze")
async def analyze(file: UploadFile = File(...), db: Session = Depends(get_db)):
    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise ApiError(413, "tooLarge", mb=settings.max_upload_mb)
    return await _analyze(db, data, file.filename or "upload")


def _load_samples() -> list[dict]:
    manifest = SAMPLES_DIR / "samples.json"
    if not manifest.exists():
        return []
    items = json.loads(manifest.read_text(encoding="utf-8"))
    return [i for i in items if (SAMPLES_DIR / i["file"]).exists()]


@router.get("/demo/samples")
def demo_samples():
    return [{k: v for k, v in s.items()} | {"thumbnail": f"/api/demo/samples/{s['id']}/image"} for s in _load_samples()]


@router.get("/demo/samples/{sample_id}/image")
def demo_sample_image(sample_id: str):
    s = next((x for x in _load_samples() if x["id"] == sample_id), None)
    if not s:
        raise ApiError(404, "sampleNotFound")
    return FileResponse(SAMPLES_DIR / s["file"])


@router.post("/demo/samples/{sample_id}/analyze")
async def demo_analyze(sample_id: str, db: Session = Depends(get_db)):
    s = next((x for x in _load_samples() if x["id"] == sample_id), None)
    if not s:
        raise ApiError(404, "sampleNotFound")
    return await _analyze(db, (SAMPLES_DIR / s["file"]).read_bytes(), s["file"], demo=True)


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    counts = dict(db.execute(select(Scan.verdict, func.count()).group_by(Scan.verdict)).all())
    recent = db.scalars(select(Scan).order_by(Scan.created_at.desc()).limit(6)).all()
    return {"total": sum(counts.values()), "ai_likely": counts.get("ai_likely", 0), "ai_edited": counts.get("ai_edited", 0),
            "authentic_likely": counts.get("authentic_likely", 0), "not_ai": counts.get("not_ai", 0),
            "manipulated_possible": counts.get("manipulated_possible", 0),
            "inconclusive": counts.get("inconclusive", 0), "recent": [_summary(s) for s in recent]}


@router.get("/scans")
def list_scans(q: str = "", verdict: str = "", limit: int = Query(100, le=500), db: Session = Depends(get_db)):
    stmt = select(Scan).order_by(Scan.created_at.desc()).limit(limit)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Scan.filename.ilike(like), Scan.id.ilike(like), Scan.sha256.ilike(like)))
    if verdict:
        stmt = stmt.where(Scan.verdict == verdict)
    return [_summary(s) for s in db.scalars(stmt).all()]


def _get(db, scan_id) -> Scan:
    s = db.get(Scan, scan_id)
    if not s:
        raise ApiError(404, "scanNotFound")
    return s


@router.get("/scans/{scan_id}")
def get_scan(scan_id: str, db: Session = Depends(get_db)):
    return _get(db, scan_id).report


@router.get("/scans/{scan_id}/image/{kind}")
def scan_image(scan_id: str, kind: str, db: Session = Depends(get_db)):
    _get(db, scan_id)
    if kind not in VISUAL_KEYS:
        raise ApiError(404, "notFound")
    p = settings.scans_dir / scan_id / f"{kind}.jpg"
    if not p.exists():
        raise ApiError(404, "notAvailable")
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


@router.get("/scans/{scan_id}/report.pdf")
def scan_pdf(scan_id: str, inline: bool = False, lang: str = "en", db: Session = Depends(get_db)):
    r = _get(db, scan_id).report
    disp = "inline" if inline else "attachment"
    return Response(build_pdf(r, norm_lang(lang)), media_type="application/pdf",
                    headers={"Content-Disposition": f'{disp}; filename="DetectiveAI-Forensic-Report-{scan_id}.pdf"'})


@router.delete("/scans/{scan_id}")
def delete_scan(scan_id: str, db: Session = Depends(get_db)):
    s = _get(db, scan_id)
    db.delete(s)
    db.commit()
    shutil.rmtree(settings.scans_dir / scan_id, ignore_errors=True)
    return {"deleted": scan_id}
