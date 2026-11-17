"""Signal-level forensics: image statistics, JPEG quantisation estimate, Error Level Analysis (ELA).

These are classic, well-documented techniques. They are *indicators*, not proof.
"""
import io

import cv2
import numpy as np
from PIL import Image, ImageChops


def jpeg_quality_estimate(img: Image.Image) -> dict | None:
    q = getattr(img, "quantization", None)
    if not q:
        return None
    luma = np.array(q.get(0, []), dtype=np.float32)
    if luma.size == 0:
        return None
    # Standard IJG luminance table scaling -> approximate quality factor
    std = np.array([16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40, 57, 69, 56,
                    14, 17, 22, 29, 51, 87, 80, 62, 18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113,
                    92, 49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99], dtype=np.float32)
    scale = float(np.mean(luma * 100 / std))
    quality = (200 - scale) / 2 if scale <= 100 else 5000 / scale
    return {"tables": len(q), "estimated_quality": int(np.clip(round(quality), 1, 100))}


def error_level_analysis(rgb: Image.Image, quality: int = 90) -> tuple[Image.Image, dict]:
    buf = io.BytesIO()
    rgb.save(buf, "JPEG", quality=quality)
    re = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
    diff = np.asarray(ImageChops.difference(rgb, re), dtype=np.float32).max(axis=2)
    mean, p99 = float(diff.mean()), float(np.percentile(diff, 99))
    # Block-level non-uniformity: coefficient of variation of 32px block means
    h, w = diff.shape
    bs = 32
    blocks = diff[: h - h % bs, : w - w % bs].reshape(h // bs, bs, w // bs, bs).mean(axis=(1, 3)) if h >= bs and w >= bs else diff
    cv = float(blocks.std() / (blocks.mean() + 1e-6))
    vis = np.clip(diff * (255.0 / max(p99, 1.0)), 0, 255).astype(np.uint8)
    vis = cv2.applyColorMap(vis, cv2.COLORMAP_INFERNO)[:, :, ::-1]
    return Image.fromarray(vis), {"mean_error": round(mean, 3), "p99_error": round(p99, 2),
                                  "block_nonuniformity": round(cv, 3), "resave_quality": quality}


def image_statistics(rgb: Image.Image) -> dict:
    a = np.asarray(rgb, dtype=np.float32)
    gray = cv2.cvtColor(a.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    # High-frequency noise residual (image minus median filtered)
    resid = gray.astype(np.float32) - cv2.medianBlur(gray, 3).astype(np.float32)
    return {
        "mean_rgb": [round(float(x), 1) for x in a.reshape(-1, 3).mean(0)],
        "std_rgb": [round(float(x), 1) for x in a.reshape(-1, 3).std(0)],
        "sharpness_laplacian_var": round(float(lap.var()), 1),
        "noise_residual_std": round(float(resid.std()), 3),
        "unique_colors_sampled": int(len(np.unique(a[::4, ::4].reshape(-1, 3).astype(np.uint8), axis=0))),
    }
