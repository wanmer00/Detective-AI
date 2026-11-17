"""Full diagnostic of one image through the production pipeline (no shortcuts, throw-away database).

Prints: detector config & preprocessing, raw logits/probabilities per view, thresholds, verdict, rules,
quality signals. Usage (from backend/):  .venv\\Scripts\\python scripts\\diagnose_image.py <image> [more images]
"""
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ["TRUTHLENS_DATA_DIR"] = tempfile.mkdtemp(prefix="detective-diag-")
os.environ["TRUTHLENS_ENABLE_SALIENCY"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.main  # noqa: E402,F401
from app.services.aggregation import aggregate as agg  # noqa: E402
from app.services.detection.detectors import registry  # noqa: E402
from app.services.face_analysis.faces import face_detector  # noqa: E402
from app.services.pipeline import run_analysis  # noqa: E402

registry.load_all()
face_detector.load()
for d in registry.ai:
    p = d.processor
    print(f"MODEL {d.spec['repo']}  device={d.device}  labels={d.id2label}  positive_idx={d.pos_idx}")
    print(f"  preprocessing: size={getattr(p, 'size', None)} resample={getattr(p, 'resample', None)} "
          f"rescale={getattr(p, 'rescale_factor', None)} mean={getattr(p, 'image_mean', None)} std={getattr(p, 'image_std', None)} "
          f"do_center_crop={getattr(p, 'do_center_crop', None)}")
print(f"THRESHOLDS: AI >= {agg.HIGH}, not-AI <= {agg.LOW}, single detector needs >= 0.90 for R2; stability >= 0.8 of views\n")

for a in sys.argv[1:]:
    path = Path(a)
    rep = run_analysis(path.read_bytes(), path.name)
    f, asm = rep["file"], rep["assessment"]
    print(f"=== {path.name}: {f['format']} {f['width']}x{f['height']}, {f['size_bytes']} bytes, "
          f"JPEG q~{(rep['signal']['jpeg'] or {}).get('estimated_quality')}, EXIF={rep['metadata']['exif_present']}")
    for d in rep["detectors"]:
        print(f"  {d['model']}: status={d['status']} median={d.get('positive_score')} full={d.get('full_image_score')} "
              f"stability={d.get('stability')} raw(full)={d.get('raw_outputs')} {d.get('inference_ms')}ms")
        print(f"    views: {json.dumps(d.get('view_scores'))}")
    print(f"  VERDICT: {asm['verdict']}  likelihood={asm['ai_likelihood']}  agreement={asm['detector_agreement']}")
    print(f"  RULES: {asm['rules_fired']}")
    print(f"  signals: " + "; ".join(f"{s['id']}={s['status']}" for s in rep["signals"]))
    print(f"  stages: {rep['stages']}\n")
