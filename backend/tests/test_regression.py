"""Regression tests on reported misclassifications (test_dataset/regression/manifest.json).

The images are run through the unmodified production pipeline. Production code never references these files,
their names or hashes; the test only checks that a known AI-generated image is no longer reported as
camera-authentic / "no AI detected". It is allowed to be Inconclusive: forcing an AI verdict on this image would
require trusting a single model that also accuses real photos (see testing/results/detector_benchmark_*).
"""
import hashlib
import json
from pathlib import Path

import pytest

from app.services.detection.detectors import registry
from app.services.pipeline import run_analysis

REG = Path(__file__).resolve().parents[2] / "test_dataset" / "regression"
CASES = json.loads((REG / "manifest.json").read_text(encoding="utf-8")) if (REG / "manifest.json").exists() else []
NOT_AI_VERDICTS = {"not_ai", "authentic_likely"}


@pytest.fixture(scope="module")
def models():
    if not registry.loaded:
        registry.load_all()
    if not any(d.available for d in registry.ai):
        pytest.skip("no AI detector weights available")
    return registry


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_known_ai_image_is_not_reported_as_real(models, case):
    data = (REG / case["file"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == case["sha256"], "regression file changed"
    r = run_analysis(data, case["file"])
    a = r["assessment"]
    if case["ground_truth"] in ("AI_GENERATED", "AI_EDITED"):
        assert a["verdict"] not in NOT_AI_VERDICTS, f"{case['id']}: {a['verdict']} via {a['rules']}"
    # whatever the verdict, every detector's own decision and the quality assessment are reported
    assert all("decision" in d for d in r["detectors"] if d["status"] == "ok")
    assert "image_quality" in a and a["detector_families"]


def test_production_code_has_no_reference_to_regression_files():
    app_dir = Path(__file__).resolve().parents[1] / "app"
    needles = [c["sha256"] for c in CASES] + [c["file"] for c in CASES] + ["known_ai_generated", "regression"]
    for f in app_dir.rglob("*.py"):
        text = f.read_text(encoding="utf-8")
        for n in needles:
            assert n not in text, f"{f} references {n}"
