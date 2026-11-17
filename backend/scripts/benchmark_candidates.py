"""Compare AI-image detectors on every labelled image already in the project (no new data collected).

Sources (labels are the official ones in each manifest):
  eval   backend/eval_images/eval_set.jsonl         20 images. NOTE: used to SELECT SwinV2 and its thresholds,
                                                    so it is biased in SwinV2's favour.
  batch  testing/batches/2026-11-17_user_batch     user-confirmed labels (REAL / AI_GENERATED / AI_EDITED / MANUALLY_EDITED)
  regr   test_dataset/regression/manifest.json     the reported false negative
  edits  backend/eval_images/edit_set.jsonl         synthetic Photoshop-style edits of real photos (EDITED only)
Derived robustness variants (computed, label inherited) for every REAL and AI_GENERATED source image:
  jpeg70 (re-save JPEG q70), wa320 (long side 320 px + JPEG q85, messenger-like), small512 (long side 512 px).

Each detector uses its own published preprocessing and decision rule. Output: JSON + markdown in
testing/results/detector_benchmark_<time>/. Usage (from backend/):  .venv\\Scripts\\python scripts\\benchmark_candidates.py
"""
import csv
import io
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

os.environ.setdefault("TRUTHLENS_DATA_DIR", __import__("tempfile").mkdtemp(prefix="detective-bench-"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pillow_heif  # noqa: E402
import timm  # noqa: E402
import torch  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402
from safetensors.torch import load_file  # noqa: E402
from transformers import AutoImageProcessor, AutoModelForImageClassification  # noqa: E402

pillow_heif.register_heif_opener()
B = Path(__file__).resolve().parents[1]
ROOT = B.parent
DEV = "cuda" if torch.cuda.is_available() else "cpu"
AI_POS = {"AI_GENERATED", "AI_EDITED", "MIXED"}
AI_NEG = {"REAL", "MANUALLY_EDITED"}


# ---------------------------------------------------------------- detectors
class SwinV2Production:
    """The production detector exactly as the app runs it (7-view median + stability rule)."""
    name = "swinv2 (production)"

    def __init__(self):
        from app.services.detection.detectors import registry
        registry.load_all()
        self.d = registry.primary

    def score(self, img):
        r = self.d.classify(img)
        s, stable = r["positive_score"], r["stable"]
        decision = "unreliable" if not stable else "ai" if s >= 0.8 else "real" if s <= 0.2 else "uncertain"
        return {"score": s, "decision": decision, "stable": stable}


class CFThermostatic:
    """timm ViT-S/16-384, resize short edge 440 -> centre crop 384, ImageNet norm, one logit, frozen calibrator."""

    def __init__(self, key):
        cfg = json.loads((B / "models_cache" / key / "config.json").read_text())
        self.name = key
        self.cal = cfg["calibration"]
        self.boundary = cfg["raw_logit_boundary"]
        self.mean, self.std = np.array(cfg["image_mean"]), np.array(cfg["image_std"])
        m = timm.create_model("vit_small_patch16_384", pretrained=False, num_classes=1)
        m.load_state_dict(load_file(str(B / "models_cache" / key / "model.safetensors")), strict=True)
        self.m = m.eval().to(DEV)

    def prep(self, img):
        w, h = img.size
        s = 440 / min(w, h)
        im = img.resize((max(384, round(w * s)), max(384, round(h * s))), Image.BICUBIC)
        W, H = im.size
        im = im.crop(((W - 384) // 2, (H - 384) // 2, (W - 384) // 2 + 384, (H - 384) // 2 + 384))
        a = (np.asarray(im, dtype=np.float32) / 255.0 - self.mean) / self.std
        return torch.from_numpy(a.transpose(2, 0, 1)).float()

    def score(self, img):
        with torch.inference_mode():
            logit = float(self.m(self.prep(img)[None].to(DEV))[0, 0])
        p = 1 / (1 + math.exp(-(self.cal["slope"] * logit + self.cal["intercept"])))
        return {"score": p, "logit": logit, "decision": "ai" if logit >= self.boundary else "real"}


class CFBuildborderless:
    """transformers ViT, CLIP preprocessing (short edge 440, crop 384), sigmoid of one logit, threshold 0.5."""
    name = "cf_vit_base"

    def __init__(self):
        p = B / "models_cache" / "cf_vit_base"
        self.proc = AutoImageProcessor.from_pretrained(p)
        self.m = AutoModelForImageClassification.from_pretrained(p).eval().to(DEV)

    def score(self, img):
        with torch.inference_mode():
            logit = float(self.m(**self.proc(images=img, return_tensors="pt").to(DEV)).logits[0, 0])
        p = 1 / (1 + math.exp(-logit))
        return {"score": p, "logit": logit, "decision": "ai" if p >= 0.5 else "real"}


# ---------------------------------------------------------------- data
def load_items():
    items = []
    for r in (json.loads(x) for x in (B / "eval_images" / "eval_set.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()):
        items.append({"src": "eval", "id": r["id"], "path": B / "eval_images" / r["file"], "label": r["label"], "group": r["id"]})
    bdir = ROOT / "testing" / "batches" / "2026-11-17_user_batch"
    with open(bdir / "manifest.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["include_in_metrics"] == "yes":
                items.append({"src": "batch", "id": r["image_id"], "path": bdir / r["file_path"], "label": r["ground_truth"],
                              "group": r["source_group_id"] or r["image_id"]})
    for r in json.loads((ROOT / "test_dataset" / "regression" / "manifest.json").read_text(encoding="utf-8")):
        items.append({"src": "regression", "id": r["id"], "path": ROOT / "test_dataset" / "regression" / r["file"],
                      "label": r["ground_truth"], "group": r["id"]})
    for r in (json.loads(x) for x in (B / "eval_images" / "edit_set.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()):
        if r["label"] == "EDITED":
            items.append({"src": "edits", "id": Path(r["file"]).stem, "path": B / "eval_images" / r["file"],
                          "label": "MANUALLY_EDITED", "group": Path(r["file"]).stem})
    return items


def jpeg(im, q):
    b = io.BytesIO()
    im.save(b, "JPEG", quality=q)
    return Image.open(io.BytesIO(b.getvalue())).convert("RGB")


def shrink(im, side):
    c = im.copy()
    c.thumbnail((side, side), Image.LANCZOS)
    return c


VARIANTS = {"original": lambda im: im, "jpeg70": lambda im: jpeg(im, 70),
            "wa320": lambda im: jpeg(shrink(im, 320), 85), "small512": lambda im: shrink(im, 512)}


# ---------------------------------------------------------------- metrics
def metrics(rows, model):
    pos = [r for r in rows if r["label"] in AI_POS]
    neg = [r for r in rows if r["label"] in AI_NEG]
    tp = sum(r[model]["decision"] == "ai" for r in pos)
    fn = sum(r[model]["decision"] == "real" for r in pos)
    fp = sum(r[model]["decision"] == "ai" for r in neg)
    tn = sum(r[model]["decision"] == "real" for r in neg)
    abst = len(rows) - tp - fn - fp - tn
    dec = tp + fn + fp + tn
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / len(pos) if pos else None  # abstentions count as misses
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else (0.0 if prec is not None and rec is not None else None)
    r3 = lambda x: None if x is None else round(x, 3)  # noqa: E731
    return {"n": len(rows), "pos": len(pos), "neg": len(neg), "TP": tp, "FN": fn, "FP": fp, "TN": tn, "abstain": abst,
            "accuracy": r3((tp + tn) / len(rows)) if rows else None, "precision": r3(prec), "recall": r3(rec), "f1": r3(f1),
            "fpr": r3(fp / len(neg)) if neg else None, "fnr": r3((len(pos) - tp) / len(pos)) if pos else None,
            "accuracy_decided": r3((tp + tn) / dec) if dec else None}


def main():
    models = [SwinV2Production(), CFThermostatic("cf_frontier"), CFThermostatic("cf_lowq"), CFBuildborderless()]
    names = [m.name for m in models]
    rows = []
    for it in load_items():
        base = ImageOps.exif_transpose(Image.open(it["path"])).convert("RGB")
        variants = VARIANTS if it["src"] in ("eval", "batch", "regression") and it["label"] in ("REAL", "AI_GENERATED") else {"original": VARIANTS["original"]}
        for vname, fn in variants.items():
            im = fn(base)
            row = {**{k: str(v) for k, v in it.items() if k != "path"}, "variant": vname, "size": f"{im.width}x{im.height}"}
            for m in models:
                row[m.name] = m.score(im)
            rows.append(row)
            print(f"{it['src']:10} {it['id']:12} {it['label']:15} {vname:9} " +
                  " ".join(f"{m.name}={row[m.name]['decision']}:{row[m.name]['score']:.3f}" for m in models), flush=True)

    out = ROOT / "testing" / "results" / f"detector_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out.mkdir(parents=True)
    (out / "raw_scores.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    cats = defaultdict(list)
    for r in rows:
        cats["ALL original images"].append(r) if r["variant"] == "original" else None
        cats[f"{r['src']} / {r['variant']}"].append(r)
        if r["variant"] != "original":
            cats[f"robustness: {r['variant']}"].append(r)
        if r["variant"] == "original" and r["src"] in ("batch", "regression"):
            cats["independent of model selection (batch + regression, original)"].append(r)
    summary = {c: {n: metrics(rs, n) for n in names} for c, rs in cats.items()}
    (out / "metrics.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    md = ["# Detector benchmark", "", f"Run {out.name}. Every number is computed from `raw_scores.json`. Recall counts abstentions "
          "(SwinV2 'uncertain'/'unreliable') as misses; `abstain` is shown separately.", ""]
    for c in sorted(summary):
        md += [f"## {c}", "", "| Model | N (AI/real) | TP | FN | FP | TN | Abstain | Accuracy | Precision | Recall | F1 | FPR | FNR |",
               "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for n in names:
            m = summary[c][n]
            md.append(f"| {n} | {m['n']} ({m['pos']}/{m['neg']}) | {m['TP']} | {m['FN']} | {m['FP']} | {m['TN']} | {m['abstain']} | "
                      f"{m['accuracy']} | {m['precision']} | {m['recall']} | {m['f1']} | {m['fpr']} | {m['fnr']} |")
        md.append("")
    (out / "report.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nwritten {out}")


if __name__ == "__main__":
    main()
