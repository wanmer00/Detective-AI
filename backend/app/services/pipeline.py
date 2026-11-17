"""End-to-end analysis pipeline shared by uploads and demo samples (identical code path)."""
import logging
import shutil
import time
from datetime import datetime, timezone

import cv2
import numpy as np
from PIL import Image

from app.core.config import settings
from app.core.security import new_scan_id, safe_filename, to_rgb, validate_image_bytes
from app.services.aggregation.aggregate import aggregate
from app.services.aggregation.signals import build_signals
from app.services.forensics.timeline import build_timeline
from app.services.detection.detectors import registry
from app.services.face_analysis.faces import analyze_faces
from app.services.forensics.metadata import analyze_metadata
from app.services.forensics.signal import error_level_analysis, image_statistics, jpeg_quality_estimate

log = logging.getLogger("truthlens.pipeline")
PREVIEW_MAX = 1600


def _save_preview(img: Image.Image, path):
    im = img.copy()
    im.thumbnail((PREVIEW_MAX, PREVIEW_MAX))
    im.save(path, "JPEG", quality=88)  # re-encoded: strips metadata, never serves the original bytes


def _saliency_overlay(rgb: Image.Image, grid: np.ndarray) -> tuple[Image.Image, dict]:
    small = rgb.copy()
    small.thumbnail((PREVIEW_MAX, PREVIEW_MAX))
    w, h = small.size
    pos = np.clip(grid, 0, None)
    norm = pos / pos.max() if pos.max() > 1e-4 else pos
    heat = cv2.resize(norm.astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    heat = np.clip(heat, 0, 1)
    cmap = cv2.applyColorMap((heat * 255).astype(np.uint8), cv2.COLORMAP_JET)[:, :, ::-1]
    base = np.asarray(small, dtype=np.float32)
    alpha = (heat[..., None] * 0.55)
    out = (base * (1 - alpha) + cmap * alpha).astype(np.uint8)
    gy, gx = np.unravel_index(int(np.argmax(grid)), grid.shape)
    return Image.fromarray(out), {"grid": grid.shape[0], "max_delta": round(float(grid.max()), 4),
                                  "min_delta": round(float(grid.min()), 4),
                                  "most_influential_cell": [int(gy), int(gx)],
                                  "meaningful": bool(grid.max() > 0.02)}


def run_analysis(data: bytes, filename: str, is_demo: bool = False) -> dict:
    t0 = time.perf_counter()
    img, info = validate_image_bytes(data, filename)
    scan_id = new_scan_id()
    scan_dir = settings.scans_dir / scan_id
    scan_dir.mkdir(parents=True)
    stages = []
    try:
        rgb = to_rgb(img)

        def stage(name, fn):
            s = time.perf_counter()
            r = fn()
            stages.append({"stage": name, "ms": round((time.perf_counter() - s) * 1000, 1)})
            return r

        _save_preview(rgb, scan_dir / "original.jpg")
        received = datetime.now(timezone.utc)
        meta = stage("metadata", lambda: analyze_metadata(data, img, info["format"]))
        timeline = stage("timeline", lambda: build_timeline(data, img, info["format"], received))
        detectors = stage("ai_detection", lambda: [d.classify(rgb) for d in registry.ai])

        saliency = {"status": "unavailable", "reason": "primary detector unavailable"}
        if settings.enable_saliency and registry.primary.available:
            try:
                grid = stage("saliency", lambda: registry.primary.occlusion_map(rgb))
                ov, stats = _saliency_overlay(rgb, grid)
                ov.save(scan_dir / "saliency.jpg", quality=88)
                saliency = {"status": "ok", "method": f"Occlusion sensitivity on {registry.primary.spec['repo']}: each "
                            "cell is blurred and the drop in the model's AI score is measured.", **stats}
            except Exception:  # noqa: BLE001
                log.exception("saliency failed")
                saliency = {"status": "error", "reason": "saliency computation failed"}
        elif not settings.enable_saliency:
            saliency = {"status": "disabled"}

        ela_img, ela = stage("ela", lambda: error_level_analysis(rgb))
        ela_img.thumbnail((PREVIEW_MAX, PREVIEW_MAX))
        ela_img.save(scan_dir / "ela.jpg", quality=88)
        signal = {**info, "jpeg": jpeg_quality_estimate(img), "ela": ela, "stats": image_statistics(rgb)}
        faces, face_ov = stage("faces", lambda: analyze_faces(rgb))
        if face_ov is not None:
            _save_preview(face_ov, scan_dir / "faces.jpg")

        assessment = stage("aggregation", lambda: aggregate(detectors, meta, signal, faces, timeline))
        file_info = {k: info[k] for k in ("format", "mime", "width", "height", "mode", "size_bytes", "sha256", "animated")}
        signals = build_signals(detectors, meta, {"jpeg": signal["jpeg"], "ela": ela}, faces, timeline, file_info)
        total_ms = round((time.perf_counter() - t0) * 1000, 1)
        visuals = {k: f"/api/scans/{scan_id}/image/{k}" for k in ("original", "saliency", "ela", "faces")
                   if (scan_dir / f"{k}.jpg").exists()}
        return {
            "scan_id": scan_id,
            "filename": safe_filename(filename),
            "created_at": received.isoformat(),
            "is_demo": is_demo,
            "file": file_info,
            "detectors": detectors,
            "metadata": meta,
            "timeline": timeline,
            "signals": signals,
            "signal": {"jpeg": signal["jpeg"], "ela": ela, "stats": signal["stats"]},
            "faces": faces,
            "saliency": saliency,
            "assessment": assessment,
            "visuals": visuals,
            "stages": stages,
            "processing_ms": total_ms,
        }
    except Exception:
        shutil.rmtree(scan_dir, ignore_errors=True)
        raise
