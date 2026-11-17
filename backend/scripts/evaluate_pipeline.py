"""Runs the FULL Detective AI pipeline (same code as uploads) on eval_images/eval_set.jsonl and scores verdicts.

Uses a throw-away data dir, so the app's scan history is not touched.
Usage (from backend/):  .venv\\Scripts\\python scripts\\evaluate_pipeline.py
"""
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

os.environ["TRUTHLENS_DATA_DIR"] = tempfile.mkdtemp(prefix="truthlens-eval-")
os.environ["TRUTHLENS_ENABLE_SALIENCY"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import os as _  # noqa: E402,F401  (applies offline env + SQLAlchemy workaround)
from app.services.detection.detectors import registry  # noqa: E402
from app.services.face_analysis.faces import face_detector  # noqa: E402
from app.services.pipeline import run_analysis  # noqa: E402

EV = Path(__file__).resolve().parents[1] / "eval_images"
registry.load_all()
face_detector.load()
rows = [json.loads(x) for x in (EV / "eval_set.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
tally = Counter()
out = []
for r in rows:
    rep = run_analysis((EV / r["file"]).read_bytes(), r["file"])
    v = rep["assessment"]["verdict"]
    truth = r["label"]
    real_v = ("authentic_likely", "not_ai")
    outcome = ("correct" if (v in ("ai_likely", "ai_edited") and truth == "AI_GENERATED") or (v in real_v and truth == "REAL")
               else "WRONG" if v in ("ai_likely", "ai_edited", *real_v) else "undecided")
    tally[(truth, outcome)] += 1
    out.append({"id": r["id"], "file": r["file"], "label": truth, "verdict": v, "outcome": outcome,
                "scores": {d["key"]: d.get("positive_score") for d in rep["detectors"]}})
    print(f"{r['id']} {truth:13} -> {v:20} {outcome:9} {out[-1]['scores']}")
(EV / "pipeline_eval_results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print()
for truth in ("AI_GENERATED", "REAL"):
    n = sum(1 for r in rows if r["label"] == truth)
    print(f"{truth:13}: correct {tally[(truth, 'correct')]}/{n} | wrong {tally[(truth, 'WRONG')]}/{n} | "
          f"undecided {tally[(truth, 'undecided')]}/{n}")
