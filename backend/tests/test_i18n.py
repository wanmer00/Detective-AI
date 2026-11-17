"""i18n: every message key emitted by the backend exists in all locales and renders without leftovers."""
import io
import os
import re
import tempfile

import pytest

os.environ.setdefault("TRUTHLENS_DATA_DIR", tempfile.mkdtemp(prefix="detective-i18n-"))
os.environ["TRUTHLENS_ENABLE_SALIENCY"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.i18n import LANGS, M, catalog, render  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def jpeg(exif=None, size=(400, 300)):
    b = io.BytesIO()
    Image.new("RGB", size, (90, 120, 150)).save(b, "JPEG", **({"exif": exif} if exif else {}))
    return b.getvalue()


def collect_msgs(obj, out):
    if isinstance(obj, dict):
        if "key" in obj and "params" in obj and isinstance(obj["key"], str):
            out.append(obj)
        for v in obj.values():
            collect_msgs(v, out)
    elif isinstance(obj, list):
        for v in obj:
            collect_msgs(v, out)
    return out


def test_catalogs_have_same_keys():
    en = set(catalog("en"))
    for lang in LANGS:
        assert set(catalog(lang)) == en, f"{lang} differs from en"


def test_render_falls_back_and_interpolates():
    assert render(M("errors.tooLarge", mb=15), "ru") == "Файл превышает лимит 15 МБ."
    assert "15" in render(M("errors.tooLarge", mb=15), "az")
    assert render(M("no.such.key"), "ru") == "no.such.key"
    assert render(M("dyn.ev.timeline", title=M("dyn.tl.chk.future_dates.title"), detail="x"), "en").startswith("Timestamp(s) in the future")


@pytest.mark.parametrize("exif_case", ["none", "camera"])
def test_every_emitted_key_exists_and_renders(client, exif_case):
    exif = None
    if exif_case == "camera":
        ex = Image.Exif()
        ex[0x010F], ex[0x0110], ex[0x0132] = "Apple", "iPhone 15", "2026:11:01 10:00:00"
        sub = ex.get_ifd(0x8769)
        sub[0x9003], sub[0x829A] = "2026:11:01 10:00:00", 0.01
        exif = ex.tobytes()
    rep = client.post("/api/analyze", files={"file": ("x.jpg", jpeg(exif), "image/jpeg")}).json()
    msgs = collect_msgs(rep, [])
    assert len(msgs) > 20
    for lang in LANGS:
        cat = catalog(lang)
        for m in msgs:
            assert m["key"] in cat, f"missing key {m['key']} in {lang}"
            text = render(m, lang)
            assert not re.search(r"\{\w+\}", text), f"unrendered placeholder in {m['key']} ({lang}): {text}"


def test_errors_carry_codes(client):
    r = client.post("/api/analyze", files={"file": ("x.jpg", b"not an image at all", "image/jpeg")})
    assert r.status_code == 400 and r.json()["code"] == "notImage" and "allowed" in r.json()["params"]
    r = client.get("/api/scans/TL-NOPE")
    assert r.status_code == 404 and r.json()["code"] == "scanNotFound"


@pytest.mark.parametrize("lang", LANGS)
def test_pdf_in_every_language(client, lang):
    sid = client.post("/api/analyze", files={"file": ("p.jpg", jpeg(), "image/jpeg")}).json()["scan_id"]
    r = client.get(f"/api/scans/{sid}/report.pdf", params={"lang": lang})
    assert r.status_code == 200 and r.content[:4] == b"%PDF" and len(r.content) > 5000


def test_pdf_unknown_language_falls_back_to_english(client):
    sid = client.post("/api/analyze", files={"file": ("p.jpg", jpeg(), "image/jpeg")}).json()["scan_id"]
    assert client.get(f"/api/scans/{sid}/report.pdf", params={"lang": "xx"}).status_code == 200
