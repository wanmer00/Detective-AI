"""Face detection (OpenCV YuNet, Haar fallback) + per-face manipulation classifier on crops."""
import logging
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.core.config import YUNET_FILE, settings
from app.services.detection.detectors import registry

log = logging.getLogger("truthlens.faces")


class FaceDetector:
    def __init__(self):
        self.backend = None
        self.error = None
        self._yunet = None
        self._haar = None

    def load(self):
        path = settings.models_dir / YUNET_FILE
        try:
            if path.exists():
                # Load from memory: OpenCV cannot open file paths containing non-ASCII characters on Windows.
                buf = np.frombuffer(path.read_bytes(), np.uint8)
                self._yunet = cv2.FaceDetectorYN.create("onnx", buf, np.array([], np.uint8), (320, 320), 0.8, 0.3, 50)
                self.backend = "OpenCV YuNet (2023mar, Apache-2.0)"
                return
        except Exception as e:  # noqa: BLE001
            log.warning("YuNet failed: %s", e)
        try:
            haar = cv2.CascadeClassifier()
            fs = cv2.FileStorage(
                (Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml").read_text(),
                cv2.FILE_STORAGE_READ | cv2.FILE_STORAGE_MEMORY)
            if not haar.read(fs.getFirstTopLevelNode()):
                raise RuntimeError("Haar cascade could not be loaded")
            self._haar = haar
            self.backend = "OpenCV Haar cascade (fallback)"
        except Exception as e:  # noqa: BLE001
            self.error = str(e)

    @property
    def available(self):
        return self.backend is not None

    def detect(self, rgb: Image.Image) -> list[dict]:
        bgr = cv2.cvtColor(np.asarray(rgb), cv2.COLOR_RGB2BGR)
        h, w = bgr.shape[:2]
        scale = min(1.0, 1280 / max(h, w))
        small = cv2.resize(bgr, (int(w * scale), int(h * scale))) if scale < 1 else bgr
        out = []
        if self._yunet is not None:
            self._yunet.setInputSize((small.shape[1], small.shape[0]))
            _, faces = self._yunet.detect(small)
            for f in faces if faces is not None else []:
                x, y, fw, fh = (f[:4] / scale).tolist()
                out.append({"box": [int(x), int(y), int(fw), int(fh)], "detection_confidence": round(float(f[-1]), 3)})
        elif self._haar is not None:
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            for x, y, fw, fh in self._haar.detectMultiScale(gray, 1.1, 5, minSize=(40, 40)):
                out.append({"box": [int(x / scale), int(y / scale), int(fw / scale), int(fh / scale)],
                            "detection_confidence": None})
        return out


face_detector = FaceDetector()


def analyze_faces(rgb: Image.Image) -> tuple[dict, Image.Image | None]:
    if not face_detector.available:
        return {"status": "unavailable", "detector": None, "error": face_detector.error, "faces": []}, None
    faces = face_detector.detect(rgb)[:12]
    clf = registry.face
    W, H = rgb.size
    for i, f in enumerate(faces):
        f["id"] = i + 1
        x, y, w, h = f["box"]
        pad = int(0.25 * max(w, h))
        crop = rgb.crop((max(0, x - pad), max(0, y - pad), min(W, x + w + pad), min(H, y + h + pad)))
        f["size_px"] = [w, h]
        if clf.available and min(w, h) >= 40:
            r = clf.classify(crop, multiview=False)
            f["manipulation_score"] = r.get("positive_score")
            f["manipulation_raw"] = r.get("raw_outputs")
            f["flagged"] = (r.get("positive_score") or 0) >= 0.85
        else:
            f["manipulation_score"] = None
            f["flagged"] = False
            f["note_key"] = "dyn.face.tooSmall" if clf.available else "dyn.face.unavailable"
            f["note"] = "face too small for the classifier" if clf.available else "face classifier unavailable"
    overlay = None
    if faces:
        overlay = rgb.copy()
        d = ImageDraw.Draw(overlay)
        lw = max(3, max(W, H) // 250)
        fs = max(14, max(W, H) // 45)
        try:
            font = ImageFont.load_default(size=fs)
        except TypeError:  # Pillow < 10.1
            font = ImageFont.load_default()
        for f in faces:
            x, y, w, h = f["box"]
            color = (255, 77, 79) if f["flagged"] else (56, 189, 248)
            d.rectangle([x, y, x + w, y + h], outline=color, width=lw)
            label = f"#{f['id']}" + (f" {f['manipulation_score']:.2f}" if f.get("manipulation_score") is not None else "")
            l, t, r, b = d.textbbox((0, 0), label, font=font)
            th, top = (b - t) + 2 * lw, max(0, y)  # YuNet boxes can start above the frame (y < 0)
            ty = top - th if top >= th else top  # label above the box when there is room, else inside its top edge
            d.rectangle([x, ty, x + (r - l) + 2 * lw, ty + th], fill=color)
            d.text((x + lw, ty + lw // 2 - t), label, fill=(0, 0, 0), font=font)
    return {
        "status": "ok",
        "detector": face_detector.backend,
        "manipulation_classifier": clf.spec["repo"] if clf.available else None,
        "manipulation_classifier_status": "ok" if clf.available else f"unavailable: {clf.error}",
        "face_count": len(faces),
        "faces": faces,
    }, overlay
