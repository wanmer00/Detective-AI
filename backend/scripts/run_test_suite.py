"""Detective AI test-suite runner.

1. Validates testing/manifest.csv (IDs, labels, links, files, SHA-256 unchanged, no overlap with eval_images).
2. Runs every image through the SAME pipeline as a normal upload (in-process, throw-away database).
3. Writes testing/results/run_<timestamp>/: predictions.csv, confusion_matrix.csv, metrics.json, report.md.

Every number in the outputs is computed from the predictions of this run. Nothing is estimated or filled in.
Usage (from backend/):  .venv\\Scripts\\python scripts\\run_test_suite.py [--only C01,C02] [--no-saliency]
"""
import argparse
import csv
import json
import math
import os
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from dataset_lib import CATEGORIES, LABELS, MANIFEST, ROOT, read_manifest, sha256  # noqa: E402

VERDICTS = ["ai_likely", "ai_edited", "authentic_likely", "not_ai", "manipulated_possible", "inconclusive"]
VERDICT_NAME = {"ai_likely": "Likely AI-generated", "ai_edited": "Likely AI-edited", "authentic_likely": "Likely authentic", "not_ai": "No AI detected",
                "manipulated_possible": "Potential manipulation", "inconclusive": "Inconclusive"}
AI_POS = {"AI_GENERATED", "AI_EDITED", "MIXED"}
AI_NEG = {"REAL", "MANUALLY_EDITED"}
NOT_AI_PRED = {"authentic_likely", "not_ai", "manipulated_possible"}
CORRECT = {  # ground truth -> verdicts counted as correct
    "REAL": {"authentic_likely", "not_ai"},
    "AI_GENERATED": {"ai_likely", "ai_edited"},
    "AI_EDITED": {"ai_edited", "ai_likely", "manipulated_possible"},
    "MANUALLY_EDITED": {"manipulated_possible"},
    "MIXED": {"ai_edited", "ai_likely", "manipulated_possible"},
}


# ---------------------------------------------------------------- validation
def validate(rows: list[dict], run: list[dict]) -> list[str]:
    errors, ids = [], set()
    for r in rows:
        rid = r.get("image_id", "")
        if not rid or rid in ids:
            errors.append(f"{rid or '<empty id>'}: missing or duplicate image_id")
        ids.add(rid)
        if r.get("test_category") not in CATEGORIES:
            errors.append(f"{rid}: invalid test_category '{r.get('test_category')}'")
    for r in run:
        rid = r["image_id"]
        p = ROOT / r.get("file_path", "")
        if not p.is_file():
            errors.append(f"{rid}: file missing ({r.get('file_path')}) - run scan_test_dataset.py")
        elif sha256(p) != r.get("sha256"):
            errors.append(f"{rid}: SHA-256 mismatch - the stored file was modified or replaced")
        o = r.get("original_image_id")
        if o and o not in ids:
            errors.append(f"{rid}: original_image_id {o} not found")
        if o == rid:
            errors.append(f"{rid}: links to itself")
    # Separation from model-selection data (backend/eval_images was used to choose models and thresholds).
    ev = HERE.parent / "eval_images"
    if ev.exists():
        tuned = {sha256(f) for f in ev.rglob("*") if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")}
        for r in rows:
            if r.get("sha256") in tuned:
                errors.append(f"{r['image_id']}: identical to an image in backend/eval_images (used for model selection)")
    return errors


# ---------------------------------------------------------------- metrics
def wilson(k: int, n: int) -> list | None:
    if n == 0:
        return None
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, c - h), 3), round(min(1, c + h), 3)]


def ratio(a, b):
    return round(a / b, 3) if b else None


def binary_ai_metrics(preds):
    m = [p for p in preds if p["ground_truth"] in AI_POS | AI_NEG]
    tp = sum(p["ground_truth"] in AI_POS and p["verdict"] in ("ai_likely", "ai_edited") for p in m)
    fn = sum(p["ground_truth"] in AI_POS and p["verdict"] in NOT_AI_PRED for p in m)
    fp = sum(p["ground_truth"] in AI_NEG and p["verdict"] in ("ai_likely", "ai_edited") for p in m)
    tn = sum(p["ground_truth"] in AI_NEG and p["verdict"] in NOT_AI_PRED for p in m)
    abst_pos = sum(p["ground_truth"] in AI_POS and p["verdict"] == "inconclusive" for p in m)
    abst_neg = sum(p["ground_truth"] in AI_NEG and p["verdict"] == "inconclusive" for p in m)
    prec, rec = ratio(tp, tp + fp), ratio(tp, tp + fn)
    if prec is None or rec is None:
        f1 = None
    else:
        f1 = round(2 * prec * rec / (prec + rec), 3) if prec + rec else 0.0
    pos, neg = tp + fn + abst_pos, fp + tn + abst_neg
    return {
        "definition": "positive = AI_GENERATED, AI_EDITED, MIXED; negative = REAL, MANUALLY_EDITED; "
                      "predicted positive = 'Likely AI-generated'; 'Inconclusive' = abstention",
        "n": len(m), "positives": pos, "negatives": neg, "TP": tp, "FP": fp, "TN": tn, "FN": fn,
        "abstained_on_positives": abst_pos, "abstained_on_negatives": abst_neg,
        "coverage": ratio(len(m) - abst_pos - abst_neg, len(m)),
        "precision": prec, "precision_95ci": wilson(tp, tp + fp),
        "recall_on_decided": rec, "recall_95ci": wilson(tp, tp + fn),
        "recall_strict": ratio(tp, pos), "f1_on_decided": f1,
        "false_positive_rate": ratio(fp, fp + tn), "false_positive_rate_95ci": wilson(fp, fp + tn),
    }


def edit_metrics(preds):
    edited = [p for p in preds if p["ground_truth"] in {"MANUALLY_EDITED", "AI_EDITED", "MIXED"}
              or "MANUALLY_EDITED" in p["secondary_labels"]]
    clean = [p for p in preds if p not in edited and p["ground_truth"] in {"REAL", "AI_GENERATED"}]
    hit = sum(p["verdict"] == "manipulated_possible" for p in edited)
    fa = sum(p["verdict"] == "manipulated_possible" for p in clean)
    return {"definition": "edited = MANUALLY_EDITED, AI_EDITED, MIXED or secondary MANUALLY_EDITED; "
                          "flagged = 'Potential manipulation'",
            "edited_images": len(edited), "flagged_as_edited": hit, "edit_detection_rate": ratio(hit, len(edited)),
            "edit_detection_rate_95ci": wilson(hit, len(edited)),
            "unedited_images": len(clean), "false_edit_alarms": fa, "false_edit_alarm_rate": ratio(fa, len(clean))}


def table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join("" if c is None else str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def breakdown(preds, key):
    g = defaultdict(Counter)
    for p in preds:
        g[p[key] or "—"][p["outcome"]] += 1
    rows = []
    for k in sorted(g):
        c = g[k]
        n = sum(c.values())
        dec = c["correct"] + c["incorrect"]
        rows.append([k, n, c["correct"], c["incorrect"], c["inconclusive"], ratio(c["correct"], dec), ratio(c["correct"], n)])
    return rows


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated categories, e.g. C01,C02")
    ap.add_argument("--no-saliency", action="store_true", help="skip occlusion maps (faster; verdicts unchanged)")
    a = ap.parse_args()

    rows = read_manifest()
    if not rows:
        raise SystemExit(f"{MANIFEST} does not exist yet. Run scripts/scan_test_dataset.py first.")
    run = [r for r in rows if r["slot_status"] == "present" and r["include_in_metrics"] == "yes"
           and r["ground_truth"] in LABELS and r["ground_truth"] != "INCONCLUSIVE"]
    if a.only:
        cats = set(a.only.split(","))
        run = [r for r in run if r["test_category"] in cats]
    skipped = [r for r in rows if r["slot_status"] in ("changed", "missing")
               or (r["slot_status"] == "present" and r not in run)]
    errors = validate(rows, run)
    if errors:
        print("Dataset validation FAILED:")
        print("\n".join("  - " + e for e in errors))
        raise SystemExit(1)
    total_by_cat = Counter(r["test_category"] for r in rows)
    run_by_cat = Counter(r["test_category"] for r in run)
    coverage_rows = [[c, CATEGORIES[c][2], total_by_cat[c], run_by_cat[c]] for c in CATEGORIES if total_by_cat[c]]
    coverage_md = table(coverage_rows, ["Category", "Description", "Planned cases", "Images evaluated"])
    out = ROOT / "results" / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if not run:
        out.mkdir(parents=True)
        (out / "report.md").write_text(
            f"# Detective AI — evaluation report ({out.name})\n\nNo test images are available yet: "
            f"0 of {len(rows)} planned cases have a file. Add images to the category folders, run "
            "`scripts/scan_test_dataset.py`, then run this script again. No metrics are reported without data.\n\n"
            f"## Coverage\n\n{coverage_md}\n", encoding="utf-8")
        print(f"No images available yet (0/{len(rows)} cases). Coverage report: {out / 'report.md'}")
        return

    os.environ["TRUTHLENS_DATA_DIR"] = tempfile.mkdtemp(prefix="detective-test-")
    if a.no_saliency:
        os.environ["TRUTHLENS_ENABLE_SALIENCY"] = "false"
    sys.path.insert(0, str(HERE.parent))
    import app.main  # noqa: F401  (offline env + SQLAlchemy workaround)
    from app.services.detection.detectors import registry
    from app.services.face_analysis.faces import face_detector
    from app.services.pipeline import run_analysis
    registry.load_all()
    face_detector.load()
    models = registry.status()

    preds = []
    for i, r in enumerate(run, 1):
        p = ROOT / r["file_path"]
        try:
            rep = run_analysis(p.read_bytes(), p.name)
        except Exception as e:  # noqa: BLE001  - a rejected/crashed file is a result too
            preds.append({**{k: r[k] for k in ("image_id", "test_category", "ground_truth", "secondary_labels",
                                               "original_image_id", "source_group_id", "origin_tool", "transformation",
                                               "transformation_tool")},
                          "verdict": "inconclusive", "verdict_label": f"ERROR: {type(e).__name__}: {e}"[:200],
                          "ai_indicator": "", "detector_median": "", "detector_stability": "", "detector_agreement": "",
                          "evidence_strength": "", "rules_fired": "", "metadata_findings": "", "timeline_warnings": "",
                          "processing_ms": "", "outcome": "inconclusive", "error": "yes"})
            print(f"[{i}/{len(run)}] {r['image_id']} ERROR {e}")
            continue
        asm, det = rep["assessment"], (rep["detectors"] or [{}])[0]
        m = rep["metadata"]
        cam = " ".join(filter(None, (m["camera"] or {}).values()))
        tl_w = [c["title"] for c in rep["timeline"]["checks"] if c["status"] == "warning"]
        findings = "; ".join(filter(None, [
            f"EXIF camera: {cam}" if cam else "no camera EXIF",
            f"software: {m['software']}" if m["software"] else "",
            f"editing tools: {', '.join(m['editing_software_detected'])}" if m["editing_software_detected"] else "",
            f"AI markers: {'; '.join(m['ai_generation_markers'])}" if m["ai_generation_markers"] else "",
            "C2PA present" if m["c2pa"]["present"] else "",
            f"JPEG q~{rep['signal']['jpeg']['estimated_quality']}" if rep["signal"].get("jpeg") else rep["file"]["format"],
        ]))
        v = asm["verdict"]
        gt = r["ground_truth"]
        outcome = "inconclusive" if v == "inconclusive" else ("correct" if v in CORRECT.get(gt, set()) else "incorrect")
        preds.append({
            "image_id": r["image_id"], "test_category": r["test_category"], "ground_truth": gt,
            "secondary_labels": r["secondary_labels"], "original_image_id": r["original_image_id"],
            "source_group_id": r["source_group_id"], "origin_tool": r["origin_tool"],
            "transformation": r["transformation"], "transformation_tool": r["transformation_tool"],
            "verdict": v, "verdict_label": asm["verdict_label"],
            "ai_indicator": "" if asm["ai_likelihood"] is None else asm["ai_likelihood"],
            "detector_median": det.get("positive_score", ""), "detector_stability": det.get("stability", ""),
            "detector_agreement": asm.get("detector_agreement", ""), "evidence_strength": asm["evidence_strength"],
            "rules_fired": " | ".join(asm["rules_fired"]), "metadata_findings": findings,
            "timeline_warnings": "; ".join(tl_w), "processing_ms": rep["processing_ms"], "outcome": outcome, "error": "",
        })
        print(f"[{i}/{len(run)}] {r['image_id']:12} {gt:16} -> {VERDICT_NAME[v]:24} {outcome}")

    # ------------------------------------------------------------ outputs
    out.mkdir(parents=True)
    with open(out / "predictions.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(preds[0].keys()))
        w.writeheader()
        w.writerows(preds)

    gts = [g for g in LABELS if g != "INCONCLUSIVE" and any(p["ground_truth"] == g for p in preds)]
    cm = {g: Counter(p["verdict"] for p in preds if p["ground_truth"] == g) for g in gts}
    with open(out / "confusion_matrix.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ground_truth \\ predicted"] + [VERDICT_NAME[v] for v in VERDICTS] + ["total"])
        for g in gts:
            w.writerow([g] + [cm[g][v] for v in VERDICTS] + [sum(cm[g].values())])

    oc = Counter(p["outcome"] for p in preds)
    groups = defaultdict(list)
    for p in preds:
        groups[p["source_group_id"]].append(p)
    weighted = sum(sum(q["outcome"] == "correct" for q in g) / len(g) for g in groups.values())
    times = sorted(float(p["processing_ms"]) for p in preds if p["processing_ms"] != "")
    metrics = {
        "run": out.name, "images_evaluated": len(preds), "independent_source_images": len(groups),
        "derived_images": sum(1 for p in preds if p["original_image_id"]),
        "outcomes": dict(oc), "accuracy_on_decided": ratio(oc["correct"], oc["correct"] + oc["incorrect"]),
        "accuracy_strict": ratio(oc["correct"], len(preds)),
        "accuracy_source_weighted": ratio(weighted, len(groups)),
        "ai_involvement": binary_ai_metrics(preds), "editing": edit_metrics(preds),
        "processing_ms": {"median": times[len(times) // 2] if times else None, "max": times[-1] if times else None},
        "models": models,
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")

    bm, em = metrics["ai_involvement"], metrics["editing"]
    fps = [p for p in preds if p["ground_truth"] in AI_NEG and p["verdict"] in ("ai_likely", "ai_edited")]
    fns = [p for p in preds if p["ground_truth"] in AI_POS and p["verdict"] in NOT_AI_PRED]
    missed_edits = [p for p in preds if p["ground_truth"] == "MANUALLY_EDITED" and p["verdict"] in {"not_ai", "authentic_likely"}]
    false_edits = [p for p in preds if p["ground_truth"] in {"REAL", "AI_GENERATED"} and "MANUALLY_EDITED" not in p["secondary_labels"]
                   and p["verdict"] == "manipulated_possible"]
    comp = Counter((p["test_category"], p["ground_truth"]) for p in preds)
    small = [c for c in CATEGORIES if c.startswith("C") and sum(n for (k, _), n in comp.items() if k == c) < 5]

    def plist(items, extra=""):
        if not items:
            return "_None._"
        return table([[p["image_id"], p["test_category"], p["ground_truth"], VERDICT_NAME[p["verdict"]], p["ai_indicator"],
                       p["detector_stability"], p["metadata_findings"], p["transformation"]] for p in items],
                     ["Image", "Cat.", "Ground truth", "Predicted", "AI indicator", "View agreement", "Metadata", "Transformation"]) + extra

    md = [f"# Detective AI — evaluation report ({out.name})", "",
          "All figures are computed from the predictions in `predictions.csv` of this run. Ground truth comes from "
          "`testing/manifest.csv` and was recorded before the run.", "",
          "## Dataset", "",
          f"- Images evaluated: **{len(preds)}** ({metrics['derived_images']} derived from other images in the set)",
          f"- Independent source images: **{len(groups)}** — derivatives of one original are NOT independent; see the "
          "source-weighted accuracy below.",
          f"- Categories with fewer than 5 images: {', '.join(small) or 'none'}",
          f"- Not evaluated (file missing/changed, label TBD, or excluded): {len(skipped)}"
          + (f" — {', '.join(r['image_id'] for r in skipped)}" if skipped else ""), "",
          "### Coverage of the 50-case plan", "", coverage_md, "",
          table([[c, CATEGORIES[c][2], g, n] for (c, g), n in sorted(comp.items())], ["Category", "Description", "Ground truth", "Images"]),
          "", "## Overall outcome", "",
          table([[oc["correct"], oc["incorrect"], oc["inconclusive"], metrics["accuracy_on_decided"], metrics["accuracy_strict"],
                  metrics["accuracy_source_weighted"]]],
                ["Correct", "Incorrect", "Inconclusive", "Accuracy (decided)", "Accuracy (inconclusive = wrong)", "Source-weighted accuracy"]),
          "", "Correctness rules: REAL → no-AI/authentic; AI_GENERATED → Likely AI; AI_EDITED and MIXED → Likely AI or "
          "Potential manipulation; MANUALLY_EDITED → Potential manipulation (a 'Likely AI' verdict on a Photoshop-only edit "
          "is counted as a false AI accusation).", "",
          "## Confusion matrix", "",
          table([[g] + [cm[g][v] for v in VERDICTS] + [sum(cm[g].values())] for g in gts],
                ["Ground truth \\ Predicted"] + [VERDICT_NAME[v] for v in VERDICTS] + ["Total"]),
          "", "## AI-involvement detection (binary)", "", bm["definition"], "",
          table([[bm["TP"], bm["FP"], bm["TN"], bm["FN"], bm["abstained_on_positives"] + bm["abstained_on_negatives"]]],
                ["TP", "FP", "TN", "FN", "Abstained"]), "",
          table([["Precision", bm["precision"], bm["precision_95ci"]], ["Recall (decided)", bm["recall_on_decided"], bm["recall_95ci"]],
                 ["Recall (abstention = miss)", bm["recall_strict"], ""], ["F1 (decided)", bm["f1_on_decided"], ""],
                 ["False-positive rate", bm["false_positive_rate"], bm["false_positive_rate_95ci"]], ["Coverage", bm["coverage"], ""]],
                ["Metric", "Value", "95% Wilson CI"]),
          "", "## Editing detection", "", em["definition"], "",
          table([[em["edited_images"], em["flagged_as_edited"], em["edit_detection_rate"], em["edit_detection_rate_95ci"],
                  em["unedited_images"], em["false_edit_alarms"], em["false_edit_alarm_rate"]]],
                ["Edited images", "Flagged", "Detection rate", "95% CI", "Unedited images", "False alarms", "False-alarm rate"]),
          "", "## False positives — authentic or manually edited images called AI", "", plist(fps),
          "", "## False negatives — AI-involved images called not-AI", "", plist(fns),
          "", "## Missed manual edits (Photoshop edits reported as clean)", "", plist(missed_edits),
          "", "## False edit alarms (clean images reported as manipulated)", "", plist(false_edits),
          "", "## Breakdown by test category", "",
          table(breakdown(preds, "test_category"), ["Category", "N", "Correct", "Incorrect", "Inconclusive", "Acc. (decided)", "Acc. (strict)"]),
          "", "## Breakdown by source tool", "",
          table(breakdown(preds, "origin_tool"), ["Origin tool", "N", "Correct", "Incorrect", "Inconclusive", "Acc. (decided)", "Acc. (strict)"]),
          "", "## Breakdown by transformation tool", "",
          table(breakdown(preds, "transformation_tool"), ["Transformation tool", "N", "Correct", "Incorrect", "Inconclusive", "Acc. (decided)", "Acc. (strict)"]),
          "", "## Processing time", "", f"Median {metrics['processing_ms']['median']} ms, max {metrics['processing_ms']['max']} ms.",
          "", "## Models", "", table([[x["model"], x["license"], x["device"] or "—", "yes" if x["available"] else "no"] for x in models],
                                     ["Model", "License", "Device", "Loaded"]),
          "", "## Caveats", "",
          "- Small samples: with 5 images per category one error moves a rate by 20 points; read the confidence intervals.",
          "- Derived images share content with their original; the source-weighted accuracy counts each source once.",
          "- `backend/eval_images` was used to choose the detector and thresholds; this test set is checked to share no files with it.",
          ""]
    (out / "report.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nResults written to {out}")


if __name__ == "__main__":
    main()
