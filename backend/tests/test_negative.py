"""Negative scenarios: hostile files, malformed input, API abuse and forensic edge cases.

Each test states the attack/failure and the behaviour we require. Uses the real app and models.
"""
import io
import os
import tempfile
import threading
import time
import zipfile

import pytest

os.environ.setdefault("TRUTHLENS_DATA_DIR", tempfile.mkdtemp(prefix="detective-neg-"))
os.environ["TRUTHLENS_ENABLE_SALIENCY"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def img_bytes(fmt="JPEG", size=(320, 240), mode="RGB", color=(120, 90, 60), **kw):
    b = io.BytesIO()
    Image.new(mode, size, color if mode in ("RGB", "RGBA", "CMYK") else 128).save(b, fmt, **kw)
    return b.getvalue()


def post(client, name, data, ctype="image/jpeg"):
    return client.post("/api/analyze", files={"file": (name, data, ctype)})


# ---------------------------------------------------------------- hostile / malformed files
def test_polyglot_jpeg_with_script_payload_is_never_served_back(client):
    payload = b"<?php system($_GET['c']); ?><script>alert(1)</script>"
    r = post(client, "poly.jpg", img_bytes() + payload)
    assert r.status_code == 200  # a valid image with trailing junk is analysed...
    sid = r.json()["scan_id"]
    preview = client.get(f"/api/scans/{sid}/image/original").content
    assert payload not in preview  # ...but only a re-encoded preview is ever stored/served


@pytest.mark.parametrize("name,data,ctype", [
    ("page.png", b"<html><script>alert(1)</script></html>", "image/png"),
    ("vector.png", b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>', "image/png"),
    ("archive.jpg", None, "image/jpeg"),
    ("empty.jpg", b"", "image/jpeg"),
    ("anim.png", b"GIF89a" + b"\x00" * 64, "image/png"),
    ("noext", b"\xff\xd8\xff\xe0" + b"\x00" * 64, "image/jpeg"),
])
def test_non_images_and_disguised_files_rejected(client, name, data, ctype):
    if data is None:
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr("x.txt", "hello")
        data = b.getvalue()
    r = post(client, name, data, ctype)
    assert r.status_code == 400, r.text
    assert "Traceback" not in r.text and "\\" not in r.json()["detail"]  # no internals leaked


def test_truncated_jpeg_rejected_cleanly(client):
    data = img_bytes(size=(800, 600))
    r = post(client, "cut.jpg", data[: len(data) // 2])
    assert r.status_code in (200, 400)
    assert r.status_code != 500


def test_corrupt_exif_segment_does_not_crash(client):
    data = img_bytes()
    junk_app1 = b"\xff\xe1\x00\x40Exif\x00\x00" + os.urandom(56)
    r = post(client, "badexif.jpg", data[:2] + junk_app1 + data[2:])
    assert r.status_code in (200, 400) and r.status_code != 500


def test_pathological_xmp_does_not_hang(client):
    """ReDoS: thousands of unclosed <rdf:li> tags in XMP must not stall the server."""
    xmp = b'<x:xmpmeta xmlns:x="adobe:ns:meta/">' + b'<rdf:li stEvt:action="x">' * 40000 + b"</x:xmpmeta>"
    data = img_bytes()
    seg = b"http://ns.adobe.com/xap/1.0/\x00" + xmp[:65000]
    data = data[:2] + b"\xff\xe1" + (len(seg) + 2).to_bytes(2, "big") + seg + data[2:]
    t = time.time()
    r = post(client, "redos.jpg", data)
    assert r.status_code in (200, 400)
    assert time.time() - t < 30, "XMP parsing is too slow (possible ReDoS)"


@pytest.mark.parametrize("fmt,mode,kw", [
    ("JPEG", "CMYK", {}), ("PNG", "L", {}), ("PNG", "LA", {}), ("PNG", "RGBA", {}),
    ("PNG", "P", {}), ("PNG", "I;16", {}), ("PNG", "1", {}), ("WEBP", "RGBA", {}),
])
def test_unusual_colour_modes_are_handled(client, fmt, mode, kw):
    ext = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[fmt]
    r = post(client, f"mode.{ext}", img_bytes(fmt, (300, 200), mode, **kw), f"image/{ext}")
    assert r.status_code == 200, f"{mode}: {r.status_code} {r.text[:200]}"


def test_animated_webp_uses_first_frame(client):
    frames = [Image.new("RGB", (200, 200), c) for c in ((255, 0, 0), (0, 255, 0))]
    b = io.BytesIO()
    frames[0].save(b, "WEBP", save_all=True, append_images=frames[1:])
    r = post(client, "anim.webp", b.getvalue(), "image/webp")
    assert r.status_code == 200 and r.json()["file"]["animated"] is True


@pytest.mark.parametrize("size", [(4000, 40), (40, 4000), (33, 33)])
def test_extreme_aspect_ratios_and_tiny_images(client, size):
    r = post(client, "odd.png", img_bytes("PNG", size), "image/png")
    assert r.status_code == 200, r.text[:200]


def test_hostile_filenames_are_sanitised(client):
    for name in ("../../etc/passwd.jpg", "<img src=x onerror=alert(1)>.jpg", "a" * 500 + ".jpg", "фото 🙂.jpg"):
        r = post(client, name, img_bytes())
        assert r.status_code == 200, name
        fn = r.json()["filename"]
        assert "/" not in fn and "<" not in fn and ".." not in fn.replace("...", "") and len(fn) <= 120


# ---------------------------------------------------------------- API abuse
def test_missing_file_field(client):
    assert client.post("/api/analyze").status_code == 422


@pytest.mark.parametrize("path", ["/..%2F..%2Fbackend%2Fapp%2Fmain.py", "/%2e%2e/%2e%2e/backend/.env",
                                  "/..%5C..%5Cbackend%5Capp%5Cmain.py", "/assets/../../backend/app/main.py"])
def test_spa_does_not_serve_files_outside_build(client, path):
    r = client.get(path)
    assert "FastAPI(" not in r.text and "TRUTHLENS_" not in r.text  # never source code or env files


def test_large_png_xmp_does_not_hang(client):
    """PNG iTXt chunks are not limited to 64 KB like JPEG APP1: try ~2 MB of unclosed tags."""
    from PIL import PngImagePlugin
    info = PngImagePlugin.PngInfo()
    info.add_itxt("XML:com.adobe.xmp", '<x:xmpmeta xmlns:x="adobe:ns:meta/">' + '<rdf:li stEvt:action="x">' * 80000
                  + "</x:xmpmeta>")
    b = io.BytesIO()
    Image.new("RGB", (300, 200), (50, 60, 70)).save(b, "PNG", pnginfo=info)
    t = time.time()
    r = post(client, "bigxmp.png", b.getvalue(), "image/png")
    assert r.status_code in (200, 400)
    assert time.time() - t < 30, f"PNG XMP took {time.time() - t:.0f}s (possible ReDoS)"


@pytest.mark.parametrize("path", ["/api/scans/TL-NOPE", "/api/scans/TL-NOPE/report.pdf",
                                  "/api/scans/TL-NOPE/image/original", "/api/nonexistent", "/api/demo/samples/../../x/image"])
def test_unknown_or_traversal_paths_return_404(client, path):
    r = client.get(path)
    assert r.status_code == 404 and "text/html" not in r.headers.get("content-type", "")


def test_sql_injection_in_search_is_harmless(client):
    for q in ("' OR 1=1 --", "%' UNION SELECT * FROM scans --", "\"; DROP TABLE scans; --"):
        r = client.get("/api/scans", params={"q": q})
        assert r.status_code == 200 and isinstance(r.json(), list)
    assert client.get("/api/stats").status_code == 200  # table still exists


def test_delete_twice(client):
    sid = post(client, "x.jpg", img_bytes()).json()["scan_id"]
    assert client.delete(f"/api/scans/{sid}").status_code == 200
    assert client.delete(f"/api/scans/{sid}").status_code == 404


def test_cors_rejects_foreign_origin(client):
    r = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert r.headers.get("access-control-allow-origin") is None


def test_security_headers(client):
    h = client.get("/api/health").headers
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"


def test_concurrent_uploads(client):
    results = []

    def go(i):
        results.append(post(client, f"c{i}.jpg", img_bytes(color=(i * 40, 50, 90))).status_code)

    ts = [threading.Thread(target=go, args=(i,)) for i in range(5)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert results == [200] * 5


# ---------------------------------------------------------------- forensic edge cases
def test_forged_camera_exif_on_flat_image_is_not_proof(client):
    """Forged EXIF must never be presented as proof; the report must say EXIF can be forged."""
    ex = Image.Exif()
    ex[0x010F], ex[0x0110], ex[0x0131] = "Apple", "iPhone 15 Pro", "17.0"
    sub = ex.get_ifd(0x8769)
    sub[0x9003], sub[0x829A], sub[0x829D] = "2026:01:01 10:00:00", 0.01, 1.8
    r = post(client, "forged.jpg", img_bytes(exif=ex.tobytes()))
    a = r.json()["assessment"]
    texts = " ".join(e["text"] for e in a["evidence_against_ai"]).lower()
    assert "forged" in texts or "copied" in texts


def test_metadata_timestamps_in_future_flagged(client):
    ex = Image.Exif()
    ex.get_ifd(0x8769)[0x9003] = "2035:01:01 10:00:00"
    j = post(client, "future.jpg", img_bytes(exif=ex.tobytes())).json()
    assert any(c["id"] == "future_dates" for c in j["timeline"]["checks"])


def test_gps_coordinates_never_exposed(client):
    ex = Image.Exif()
    gps = ex.get_ifd(0x8825)
    gps[1], gps[2], gps[3], gps[4] = "N", (55.0, 45.0, 0.0), "E", (37.0, 37.0, 0.0)
    j = post(client, "gps.jpg", img_bytes(exif=ex.tobytes())).json()
    blob = str(j)
    assert "55.0, 45.0" not in blob and "37.0, 37.0" not in blob


def test_same_bytes_same_verdict(client):
    data = img_bytes(color=(10, 200, 30))
    a = post(client, "a.jpg", data).json()["assessment"]["verdict"]
    b = post(client, "b.jpg", data).json()["assessment"]["verdict"]
    assert a == b
