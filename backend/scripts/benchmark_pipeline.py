"""Before/after benchmark of the FULL Detective AI pipeline (same code path as an upload) on every labelled
image already in the project. No new data is collected; labels come from the existing manifests.

  before = SwinV2 only, no quality gate    (TRUTHLENS_DETECTORS=swinv2_ai_detector, gate disabled)
  after  = SwinV2 + Community Forensics family vote + quality gate   (current defaults)

Each configuration runs in its own process (settings are read at import). Derived robustness variants are
created in memory for every REAL / AI_GENERATED source image: jpeg70 (re-saved JPEG q70, metadata dropped),
wa320 (long side 320 px + JPEG q85: messenger-like), small512 (long side 512 px, PNG).
Output: testing/results/pipeline_benchmark_<time>/{predictions_<cfg>.json, metrics.json, report.md}

Usage (from backend/):  .venv\\Scripts\\python scripts\\benchmark_pipeline.py
"""
import io
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
B = HERE.parent
ROOT = B.parent
CONFIGS = {
    "before": {"TRUTHLENS_DETECTORS": "swinv2_ai_detector", "TRUTHLENS_LOW_QUALITY_LONG_SIDE": "0",
               "TRUTHLENS_LOW_QUALITY_JPEG": "-1"},
    "after": {},
}
VERDICTS = ["ai_likely", "ai_edited", "authentic_likely", "not_ai", "manipulated_possible", "inconclusive"]
AI_PRED = {"ai_likely", "ai_edited"}
NOT_AI_PRED = {"authentic_likely", "not_ai", "manipulated_possible"}
AI_POS = {"AI_GENERATED", "AI_EDITED"}
AI_NEG = {"REAL", "MANUALLY_EDITED"}
CORRECT = {"REAL": {"authentic_likely", "not_ai"}, "AI_GENERATED": AI_PRED,
           "AI_EDITED": {"ai_edited", "ai_likely", "manipulated_possible"}, "MANUALLY_EDITED": {"manipulated_possible"}}


def variants_bytes(path: Path):
    from PIL import Image, ImageOps

    base = ImageOps.exif_transpose(Image.open(path)).convert("RGB")

    def enc(im, fmt, **kw):
        b = io.BytesIO()
        im.save(b, fmt, **kw)
        return b.getvalue()

    def shrink(side):
        c = base.copy()
        c.thumbnail((side, side), Image.LANCZOS)
        return c

    return {"jpeg70": (enc(base, "JPEG", quality=70), ".jpg"), "wa320": (enc(shrink(320), "JPEG", quality=85), ".jpg"),
            "small512": (enc(shrink(512), "PNG"), ".png")}


def worker(cfg: str, out: Path):
    os.environ["TRUTHLENS_DATA_DIR"] = tempfile.mkdtemp(prefix=f"detective-pbench-{cfg}-")
    os.environ["TRUTHLENS_ENABLE_SALIENCY"] = "false"
    sys.path.insert(0, str(B))
    sys.path.insert(0, str(HERE))
    import pillow_heif

    pillow_heif.register_heif_opener()
    from app.main import os as _  # noqa: F401  (applies offline env + SQLAlchemy workaround)
    from app.services.detection.detectors import registry
    from app.services.face_analysis.faces import face_detector
    from app.services.pipeline import run_analysis
    from benchmark_candidates import load_items

    registry.load_all()
    face_detector.load()
    print(cfg, "detectors:", [(m.spec["key"], m.available) for m in registry.ai], flush=True)
    preds = []
    for it in load_items():
        jobs = [("original", it["path"].read_bytes(), it["path"].name)]
        if it["src"] in ("eval", "batch", "regression") and it["label"] in ("REAL", "AI_GENERATED"):
            jobs += [(v, data, f"{it['id']}_{v}{ext}") for v, (data, ext) in variants_bytes(it["path"]).items()]
        for variant, data, name in jobs:
            r = run_analysis(data, name)
            a = r["assessment"]
            preds.append({"src": it["src"], "id": it["id"], "label": it["label"], "variant": variant,
                          "size": f"{r['file']['width']}x{r['file']['height']}", "verdict": a["verdict"], "rules": a["rules"],
                          "confidence": (a.get("detection_confidence") or {}).get("level"),
                          "detectors": {d["key"]: {"decision": d.get("decision"), "score": d.get("positive_score")}
                                        for d in r["detectors"] if d["status"] == "ok"}})
            print(f"{cfg:6} {it['src']:10} {it['id']:12} {it['label']:15} {variant:9} -> {a['verdict']:20} {a['rules']}", flush=True)
    out.write_text(json.dumps(preds, indent=1), encoding="utf-8")


def metrics(rows):
    pos = [r for r in rows if r["label"] in AI_POS]
    neg = [r for r in rows if r["label"] in AI_NEG]
    tp = sum(r["verdict"] in AI_PRED for r in pos)
    fn_real = sum(r["verdict"] in NOT_AI_PRED for r in pos)  # AI image reported as not-AI: the dangerous error
    fp = sum(r["verdict"] in AI_PRED for r in neg)
    tn = sum(r["verdict"] in NOT_AI_PRED for r in neg)
    unc = sum(r["verdict"] == "inconclusive" for r in rows)
    correct = sum(r["verdict"] in CORRECT[r["label"]] for r in rows)
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / len(pos) if pos else None
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else (0.0 if prec is not None and rec is not None else None)
    r3 = lambda x: None if x is None else round(x, 3)  # noqa: E731
    return {"n": len(rows), "ai": len(pos), "not_ai": len(neg), "TP": tp, "FN_reported_real": fn_real,
            "FN_inconclusive": len(pos) - tp - fn_real, "FP": fp, "TN": tn, "inconclusive": unc,
            "accuracy": r3(correct / len(rows)) if rows else None, "precision": r3(prec), "recall": r3(rec), "f1": r3(f1),
            "fpr": r3(fp / len(neg)) if neg else None, "fnr": r3((len(pos) - tp) / len(pos)) if pos else None,
            "false_real_rate": r3(fn_real / len(pos)) if pos else None,
            "inconclusive_rate": r3(unc / len(rows)) if rows else None,
            "confusion": {lab: dict(Counter(r["verdict"] for r in rows if r["label"] == lab)) for lab in sorted({r["label"] for r in rows})}}


def categories(preds):
    cats = defaultdict(list)
    for r in preds:
        if r["variant"] == "original":
            cats["1 all originals"].append(r)
            if r["src"] in ("batch", "regression"):
                cats["2 independent of model selection (user batch + regression)"].append(r)
            if r["src"] == "eval":
                cats["3 eval_set (used to pick SwinV2: biased)"].append(r)
            if r["src"] == "edits":
                cats["8 Photoshop-style manual edits (edit_set)"].append(r)
            if r["label"] in ("AI_EDITED", "MANUALLY_EDITED") and r["src"] == "batch":
                cats["9 user-batch edited images (AI_EDITED + MANUALLY_EDITED)"].append(r)
        else:
            name = {"jpeg70": "4 re-compressed JPEG q70", "wa320": "5 messenger-like 320 px + JPEG q85",
                    "small512": "6 resized to 512 px"}[r["variant"]]
            cats[name].append(r)
            cats["7 all degraded variants"].append(r)
    return dict(sorted(cats.items()))


def report(out: Path):
    preds = {c: json.loads((out / f"predictions_{c}.json").read_text(encoding="utf-8")) for c in CONFIGS}
    summary = {c: {name: metrics(rows) for name, rows in categories(p).items()} for c, p in preds.items()}
    (out / "metrics.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    md = ["# Pipeline benchmark: before vs after", "",
          f"Run `{out.name}`. Full production pipeline (metadata, timeline, detectors, faces, aggregation; saliency off).",
          "Every number is computed from `predictions_before.json` / `predictions_after.json` in this folder.", "",
          "* **before** = SwinV2 only, no quality gate. **after** = SwinV2 + Community Forensics family + quality gate.",
          "* AI-positive verdicts: ai_likely, ai_edited. Not-AI verdicts: not_ai, authentic_likely, manipulated_possible. "
          "Inconclusive is an abstention: it counts as a miss in recall/FNR, never as a hit.",
          "* `false real` = AI image reported with a not-AI verdict (the dangerous error). `accuracy` = exact expected "
          "verdict class (REAL→not_ai/authentic, AI→ai_likely/ai_edited, MANUALLY_EDITED→manipulated_possible).", ""]
    for name in summary["after"]:
        md += [f"## {name[2:]}", "", "| Config | N (AI/not-AI) | TP | False real | FN inconcl. | FP | TN | Inconcl. | Accuracy | Precision | Recall | F1 | FPR | FNR |",
               "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for c in CONFIGS:
            m = summary[c].get(name)
            if m:
                md.append(f"| {c} | {m['n']} ({m['ai']}/{m['not_ai']}) | {m['TP']} | {m['FN_reported_real']} | {m['FN_inconclusive']} | {m['FP']} | "
                          f"{m['TN']} | {m['inconclusive']} | {m['accuracy']} | {m['precision']} | {m['recall']} | {m['f1']} | {m['fpr']} | {m['fnr']} |")
        md += ["", "Confusion matrix (rows = ground truth, columns = verdict):", "",
               "| Config | Ground truth | " + " | ".join(VERDICTS) + " |", "|---|---|" + "---|" * len(VERDICTS)]
        for c in CONFIGS:
            for lab, cnt in summary[c][name]["confusion"].items():
                md.append(f"| {c} | {lab} | " + " | ".join(str(cnt.get(v, 0)) for v in VERDICTS) + " |")
        md.append("")
    reg = {c: [r for r in p if r["src"] == "regression"] for c, p in preds.items()}
    md += ["## Regression images", "", "| Config | ID | Variant | Verdict | Rules | Detector decisions |", "|---|---|---|---|---|---|"]
    for c, rows in reg.items():
        for r in rows:
            dd = ", ".join(f"{k}={v['decision']} {v['score']:.3f}" for k, v in r["detectors"].items())
            md.append(f"| {c} | {r['id']} | {r['variant']} | {r['verdict']} | {' '.join(r['rules'])} | {dd} |")
    (out / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"written {out}")


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        return worker(sys.argv[2], Path(sys.argv[3]))
    if len(sys.argv) == 3 and sys.argv[1] == "--report":
        return report(Path(sys.argv[2]))
    out = ROOT / "testing" / "results" / f"pipeline_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out.mkdir(parents=True)
    for cfg, env in CONFIGS.items():
        subprocess.run([sys.executable, __file__, "--worker", cfg, str(out / f"predictions_{cfg}.json")],
                       env={**os.environ, **env, "DISABLE_SQLALCHEMY_CEXT_RUNTIME": "1"}, check=True)
    report(out)


if __name__ == "__main__":
    main()
