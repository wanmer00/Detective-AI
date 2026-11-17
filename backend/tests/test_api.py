"""API integration tests. Run from backend/:  .venv\\Scripts\\python -m pytest -q

Uses the real models when they are downloaded (TRUTHLENS_SKIP_MODELS unset). Tests that need
real inference are skipped automatically if the primary detector is unavailable.
"""
import io
import os
import tempfile
from pathlib import Path

import pytest

_tmp = os.environ.setdefault("TRUTHLENS_DATA_DIR", tempfile.mkdtemp(prefix="truthlens-test-"))  # isolated DB & scans

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import app  # noqa: E402
from app.services.detection.detectors import registry  # noqa: E402

SAMPLES = Path(__file__).resolve().parents[2] / "sample_images"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _png(w=256, h=256, color=(120, 80, 200)) -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (w, h), color).save(b, "PNG")
    return b.getvalue()


def test_health(client):
    r = client.get("/api/health").json()
    assert r["backend"] and r["database"]
    assert {m["key"] for m in r["models"]} >= {"swinv2_ai_detector"}


def test_rejects_non_image(client):
    r = client.post("/api/analyze", files={"file": ("evil.jpg", b"MZ\x90\x00 not an image", "image/jpeg")})
    assert r.status_code == 400 and "not a valid" in r.json()["detail"]


def test_rejects_bad_extension(client):
    r = client.post("/api/analyze", files={"file": ("x.gif", _png(), "image/gif")})
    assert r.status_code == 400


@pytest.mark.parametrize("fmt,ext", [("AVIF", "avif"), ("HEIF", "heic")])
def test_accepts_avif_and_heic(client, fmt, ext):
    from app.core.security import ALLOWED_FORMATS
    if fmt not in ALLOWED_FORMATS:
        pytest.skip(f"{fmt} decoder not installed")
    b = io.BytesIO()
    try:
        Image.new("RGB", (128, 96), (30, 120, 200)).save(b, fmt)
    except Exception:  # noqa: BLE001
        pytest.skip(f"no {fmt} encoder available to build the test file")
    r = client.post("/api/analyze", files={"file": (f"t.{ext}", b.getvalue(), f"image/{ext}")})
    assert r.status_code == 200, r.text
    assert r.json()["file"]["format"] == fmt


def test_rejects_tiny(client):
    r = client.post("/api/analyze", files={"file": ("t.png", _png(8, 8), "image/png")})
    assert r.status_code == 400


def test_rejects_decompression_bomb(client):
    b = io.BytesIO()
    Image.new("1", (9000, 9000)).save(b, "PNG")  # 81 MP, tiny file
    r = client.post("/api/analyze", files={"file": ("bomb.png", b.getvalue(), "image/png")})
    detail = r.json()["detail"].lower()
    assert r.status_code == 400 and ("large" in detail or "bomb" in detail)


def test_rejects_oversize(client):
    big = b"\x89PNG\r\n\x1a\n" + b"0" * (16 * 1024 * 1024)
    r = client.post("/api/analyze", files={"file": ("big.png", big, "image/png")})
    assert r.status_code in (400, 413)


def test_full_flow(client):
    r = client.post("/api/analyze", files={"file": ("flat.png", _png(), "image/png")})
    assert r.status_code == 200, r.text
    rep = r.json()
    sid = rep["scan_id"]
    assert len(rep["file"]["sha256"]) == 64
    assert rep["assessment"]["verdict"] in {"ai_likely", "authentic_likely", "not_ai", "manipulated_possible", "inconclusive"}
    for d in rep["detectors"]:
        assert d["status"] in {"ok", "unavailable", "error"}
        if d["status"] == "ok":
            assert 0.0 <= d["positive_score"] <= 1.0 and d["raw_outputs"]
    # persistence + history + stats
    assert client.get(f"/api/scans/{sid}").json()["scan_id"] == sid
    assert any(s["scan_id"] == sid for s in client.get("/api/scans", params={"q": "flat"}).json())
    assert client.get("/api/stats").json()["total"] >= 1
    # visuals served only via API, metadata stripped
    img = client.get(f"/api/scans/{sid}/image/original")
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"
    assert client.get(f"/api/scans/{sid}/image/../../etc").status_code == 404
    # pdf
    pdf = client.get(f"/api/scans/{sid}/report.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    # delete removes record and files
    assert client.delete(f"/api/scans/{sid}").status_code == 200
    assert client.get(f"/api/scans/{sid}").status_code == 404
    assert not (Path(_tmp) / "scans" / sid).exists()


def test_deterministic_inference(client):
    if not registry.primary.available:
        pytest.skip("model not downloaded")
    data = _png(300, 300, (10, 200, 30))
    a = client.post("/api/analyze", files={"file": ("a.png", data, "image/png")}).json()
    b = client.post("/api/analyze", files={"file": ("b.png", data, "image/png")}).json()
    assert a["detectors"][0]["positive_score"] == pytest.approx(b["detectors"][0]["positive_score"], abs=1e-3)


@pytest.mark.parametrize("sample", ["real-people", "ai-zvd"])
def test_demo_samples_use_real_pipeline(client, sample):
    if not (SAMPLES / "samples.json").exists():
        pytest.skip("no samples")
    r = client.post(f"/api/demo/samples/{sample}/analyze")
    assert r.status_code == 200
    rep = r.json()
    assert rep["is_demo"] is True and rep["stages"]
