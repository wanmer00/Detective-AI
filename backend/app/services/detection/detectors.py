"""Pretrained AI-generated image detectors (Hugging Face transformers, local weights only).

Nothing here invents a score: if a model fails to load or run, the result is marked unavailable.
"""
import logging
import threading
import time

import numpy as np
from PIL import Image, ImageFilter

from app.core.config import AI_DETECTORS, FACE_MANIPULATION_MODEL, settings

log = logging.getLogger("truthlens.detection")


def _device():
    import torch

    if settings.device == "cpu":
        return "cpu"
    if settings.device == "cuda" or torch.cuda.is_available():
        return "cuda" if torch.cuda.is_available() else "cpu"
    return "cpu"


class HFClassifier:
    """Wraps a local image-classification checkpoint and maps its labels to a 'positive' class."""

    def __init__(self, spec: dict, positive_labels: list[str]):
        self.spec = spec
        self.positive_labels = [p.lower() for p in positive_labels]
        self.path = settings.models_dir / spec["key"]
        self.model = None
        self.processor = None
        self.error: str | None = None
        self.device = "cpu"
        self.id2label: dict[int, str] = {}
        self.pos_idx: list[int] = []
        self.revision = None
        self.lock = threading.Lock()

    @property
    def available(self) -> bool:
        return self.model is not None

    def load(self) -> None:
        try:
            import torch
            from transformers import AutoImageProcessor, AutoModelForImageClassification

            if not (self.path / "config.json").exists():
                raise FileNotFoundError("weights not downloaded (run scripts/download_models.py)")
            self.device = _device()
            self.processor = AutoImageProcessor.from_pretrained(self.path, local_files_only=True)
            model = AutoModelForImageClassification.from_pretrained(self.path, local_files_only=True)
            model.eval().to(self.device)
            self.id2label = {int(k): v for k, v in model.config.id2label.items()}
            self.pos_idx = [i for i, l in self.id2label.items() if l.lower() in self.positive_labels]
            if not self.pos_idx:
                raise ValueError(f"no positive label among {list(self.id2label.values())}")
            self.revision = getattr(model.config, "transformers_version", None)
            self.model = model
            self._torch = torch
            log.info("Loaded %s on %s labels=%s", self.spec["repo"], self.device, self.id2label)
        except Exception as e:  # noqa: BLE001
            self.error = f"{type(e).__name__}: {e}"
            log.warning("Model %s unavailable: %s", self.spec["repo"], self.error)

    def predict_batch(self, images: list[Image.Image]) -> np.ndarray:
        """Returns softmax probabilities, shape (N, num_labels)."""
        torch = self._torch
        with self.lock, torch.inference_mode():
            inputs = self.processor(images=images, return_tensors="pt").to(self.device)
            logits = self.model(**inputs).logits
            return torch.softmax(logits.float(), dim=-1).cpu().numpy()

    @staticmethod
    def views(img: Image.Image) -> dict[str, Image.Image]:
        """Several views of the same image. A trustworthy decision should not flip between them."""
        W, H = img.size
        return {
            "full": img,
            "flip": img.transpose(Image.FLIP_LEFT_RIGHT),
            "top": img.crop((0, 0, W, H // 2)),
            "bottom": img.crop((0, H // 2, W, H)),
            "left": img.crop((0, 0, W // 2, H)),
            "right": img.crop((W // 2, 0, W, H)),
            "center": img.crop((W // 5, H // 5, W - W // 5, H - H // 5)),
        }

    def classify(self, img: Image.Image, multiview: bool = True) -> dict:
        """Multi-view scoring: the reported score is the MEDIAN over views, and `stability` is the share of
        views on the same side of 0.5 as that median. Single-pass scores proved unstable (one phone photo
        scored 0.97 whole, 0.04 top half, 0.01 bottom half)."""
        base = {
            "key": self.spec["key"],
            "model": self.spec["repo"],
            "architecture": self.spec["arch"],
            "license": self.spec["license"],
            "role": self.spec.get("role"),
            "family": self.spec.get("family", self.spec["key"]),
            "name": self.spec.get("name", self.spec["repo"]),
        }
        if not self.available:
            return {**base, "status": "unavailable", "error": self.error}
        try:
            t0 = time.perf_counter()
            views = self.views(img) if multiview else {"full": img}
            probs = self.predict_batch(list(views.values()))
            ms = (time.perf_counter() - t0) * 1000
            per_view = {k: float(p[self.pos_idx].sum()) for k, p in zip(views, probs)}
            scores = np.array(list(per_view.values()))
            med = float(np.median(scores))
            stability = float(np.mean((scores >= 0.5) == (med >= 0.5)))
            return {
                **base,
                "status": "ok",
                "device": self.device,
                "transformers_version": self.revision,
                "positive_score": round(med, 4),
                "full_image_score": round(per_view["full"], 4),
                "view_scores": {k: round(v, 4) for k, v in per_view.items()},
                "stability": round(stability, 3),
                "stable": stability >= 0.8,
                # Decision rule for this detector (uncalibrated softmax): AI >= 0.80, not-AI <= 0.20, only when stable.
                "decision": ("unreliable" if stability < 0.8 else "ai" if med >= 0.8 else "real" if med <= 0.2 else "uncertain"),
                "threshold": "AI ≥ 0.80 · not-AI ≤ 0.20 (7-view median, ≥80% views agree)",
                "score_kind": "raw",
                "input": f"{img.width}×{img.height} → 256×256 (resized, aspect not preserved)",
                "raw_outputs": {self.id2label[i]: round(float(p), 4) for i, p in enumerate(probs[0])},
                "inference_ms": round(ms, 1),
            }
        except Exception as e:  # noqa: BLE001
            log.exception("Inference failed for %s", self.spec["repo"])
            return {**base, "status": "error", "error": type(e).__name__}

    def occlusion_map(self, img: Image.Image, grid: int = 8) -> np.ndarray | None:
        """Real model-derived saliency: drop in positive-class score when each cell is blurred out.

        Returns a (grid, grid) array of score deltas (positive => region pushes the model towards 'AI').
        """
        if not self.available:
            return None
        small = img.copy()
        small.thumbnail((512, 512))
        blurred = small.filter(ImageFilter.GaussianBlur(radius=12))
        w, h = small.size
        base = float(self.predict_batch([small])[0][self.pos_idx].sum())
        variants, cells = [], []
        for gy in range(grid):
            for gx in range(grid):
                box = (gx * w // grid, gy * h // grid, (gx + 1) * w // grid, (gy + 1) * h // grid)
                v = small.copy()
                v.paste(blurred.crop(box), box)
                variants.append(v)
                cells.append((gy, gx))
        out = np.zeros((grid, grid), dtype=np.float32)
        for i in range(0, len(variants), 16):
            probs = self.predict_batch(variants[i:i + 16])
            for (gy, gx), p in zip(cells[i:i + 16], probs):
                out[gy, gx] = base - float(p[self.pos_idx].sum())
        return out


class CFDetector:
    """Community Forensics ViT-S/16-384 (timm) with the author's published preprocessing and frozen calibrator.

    Preprocessing (from the model's config.json): RGB, resize short edge to 440 (bicubic), centre-crop 384×384,
    ImageNet normalisation. Output: one raw logit. Decision: logit >= raw_logit_boundary. The calibrated probability
    uses the author's frozen Platt/bias calibrator, fitted on THEIR calibration cohort - it is not validated on
    Detective AI's data, so it is reported as a vendor-calibrated score, not as a ground-truth probability.
    """

    def __init__(self, spec: dict):
        self.spec = spec
        self.path = settings.models_dir / spec["key"]
        self.model = None
        self.error: str | None = None
        self.device = "cpu"
        self.lock = threading.Lock()

    @property
    def available(self) -> bool:
        return self.model is not None

    def load(self) -> None:
        try:
            import json

            import timm
            import torch
            from safetensors.torch import load_file

            cfg = json.loads((self.path / "config.json").read_text())
            self.cal = cfg["calibration"]
            self.boundary = float(cfg["raw_logit_boundary"])
            self.size, self.short = int(cfg["input_size"]), int(cfg["resize_short_edge"])
            self.mean = np.array(cfg["image_mean"], dtype=np.float32)
            self.std = np.array(cfg["image_std"], dtype=np.float32)
            self.device = _device()
            weights = self.path / "model.safetensors"
            if self.spec.get("sha256"):
                import hashlib

                digest = hashlib.sha256(weights.read_bytes()).hexdigest()
                if digest != self.spec["sha256"]:
                    raise ValueError(f"weights differ from the benchmarked file (sha256 {digest[:12]}…)")
            m = timm.create_model("vit_small_patch16_384", pretrained=False, num_classes=1)
            m.load_state_dict(load_file(str(weights)), strict=True)
            self.model = m.eval().to(self.device)
            self._torch = torch
            log.info("Loaded %s on %s (boundary %.4f)", self.spec["repo"], self.device, self.boundary)
        except Exception as e:  # noqa: BLE001
            self.error = f"{type(e).__name__}: {e}"
            log.warning("Model %s unavailable: %s", self.spec["repo"], self.error)

    def _prep(self, img: Image.Image):
        w, h = img.size
        s = self.short / min(w, h)
        im = img.resize((max(self.size, round(w * s)), max(self.size, round(h * s))), Image.BICUBIC)
        W, H = im.size
        left, top = (W - self.size) // 2, (H - self.size) // 2
        im = im.crop((left, top, left + self.size, top + self.size))
        a = (np.asarray(im, dtype=np.float32) / 255.0 - self.mean) / self.std
        return self._torch.from_numpy(a.transpose(2, 0, 1).copy())

    def calibrated(self, logit: float) -> float:
        return float(1 / (1 + np.exp(-(self.cal["slope"] * logit + self.cal["intercept"]))))

    def classify(self, img: Image.Image) -> dict:
        base = {"key": self.spec["key"], "model": self.spec["repo"], "architecture": self.spec["arch"],
                "license": self.spec["license"], "role": self.spec.get("role"), "family": self.spec["family"],
                "name": self.spec.get("name", self.spec["repo"])}
        if not self.available:
            return {**base, "status": "unavailable", "error": self.error}
        try:
            t0 = time.perf_counter()
            with self.lock, self._torch.inference_mode():
                logit = float(self.model(self._prep(img)[None].to(self.device))[0, 0])
            ms = (time.perf_counter() - t0) * 1000
            p = self.calibrated(logit)
            return {**base, "status": "ok", "device": self.device, "positive_score": round(p, 4),
                    "raw_logit": round(logit, 4), "stable": True,
                    "decision": "ai" if logit >= self.boundary else "real",
                    "threshold": f"raw logit ≥ {self.boundary:.4f} (≈ calibrated 0.65)",
                    "score_kind": "vendor_calibrated",
                    "input": f"{img.width}×{img.height} → short edge {self.short} → centre crop {self.size}×{self.size}",
                    "raw_outputs": {"logit": round(logit, 4)}, "inference_ms": round(ms, 1)}
        except Exception as e:  # noqa: BLE001
            log.exception("Inference failed for %s", self.spec["repo"])
            return {**base, "status": "error", "error": type(e).__name__}


class DetectorRegistry:
    def __init__(self):
        wanted = {k.strip() for k in settings.detectors.split(",") if k.strip()}
        self.ai = [CFDetector(s) if s.get("kind") == "timm_cf" else HFClassifier(s, s["ai_labels"])
                   for s in AI_DETECTORS if s["key"] in wanted]
        self.face = HFClassifier(FACE_MANIPULATION_MODEL, FACE_MANIPULATION_MODEL["fake_labels"])
        self.loaded = False

    def load_all(self):
        for m in [*self.ai, self.face]:
            m.load()
        self.loaded = True

    @property
    def primary(self) -> HFClassifier:
        """The HF detector used for occlusion saliency (needs predict_batch)."""
        return next((m for m in self.ai if isinstance(m, HFClassifier)), self.ai[0])

    def status(self) -> list[dict]:
        return [
            {"key": m.spec["key"], "model": m.spec["repo"], "license": m.spec["license"],
             "available": m.available, "device": m.device if m.available else None, "error": m.error}
            for m in [*self.ai, self.face]
        ]


registry = DetectorRegistry()
