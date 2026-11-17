import io
from datetime import datetime, timezone

from PIL import Image

from app.services.forensics.timeline import build_timeline

SCAN = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)


def _jpeg(exif_base: dict, exif_sub: dict, xmp: bytes = b"") -> tuple[bytes, Image.Image]:
    img = Image.new("RGB", (64, 64), (90, 90, 90))
    ex = Image.Exif()
    for k, v in exif_base.items():
        ex[k] = v
    sub = ex.get_ifd(0x8769)
    for k, v in exif_sub.items():
        sub[k] = v
    b = io.BytesIO()
    img.save(b, "JPEG", exif=ex.tobytes())
    data = b.getvalue()
    if xmp:  # proper APP1 XMP segment right after SOI
        payload = b"http://ns.adobe.com/xap/1.0/\x00" + xmp
        data = data[:2] + b"\xff\xe1" + (len(payload) + 2).to_bytes(2, "big") + payload + data[2:]
    return data, Image.open(io.BytesIO(data))


def ids(t):
    return {c["id"]: c["status"] for c in t["checks"]}


def test_no_metadata_is_info_not_warning():
    b = io.BytesIO()
    Image.new("RGB", (64, 64)).save(b, "PNG")
    t = build_timeline(b.getvalue(), Image.open(io.BytesIO(b.getvalue())), "PNG", SCAN)
    assert ids(t) == {"no_timestamps": "info"}
    assert t["events"][-1]["source"] == "Detective AI"


def test_consistent_camera_dates():
    data, img = _jpeg({0x0132: "2026:11:17 10:00:30", 0x0131: "iOS 19.1"}, {0x9003: "2026:11:17 10:00:00"})
    c = ids(build_timeline(data, img, "JPEG", SCAN))
    assert c["capture_modify_consistent"] == "ok"
    assert "modify_before_capture" not in c


def test_modify_before_capture_is_flagged():
    data, img = _jpeg({0x0132: "2026:01:01 10:00:00"}, {0x9003: "2026:06:01 10:00:00"})
    assert ids(build_timeline(data, img, "JPEG", SCAN))["modify_before_capture"] == "warning"


def test_future_date_is_flagged():
    data, img = _jpeg({}, {0x9003: "2031:01:01 10:00:00"})
    assert ids(build_timeline(data, img, "JPEG", SCAN))["future_dates"] == "warning"


def test_iphone_photoshop_namespace_is_not_editing():
    """iPhones write XMP `photoshop:DateCreated`; that namespace must not be read as Photoshop editing."""
    from app.services.forensics.metadata import analyze_metadata
    xmp = (b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF><rdf:Description xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/" '
           b'xmp:CreatorTool="18.6.2" photoshop:DateCreated="2026-11-08T16:53:01"/></rdf:RDF></x:xmpmeta>')
    data, img = _jpeg({0x010F: "Apple", 0x0110: "iPhone 11 Pro", 0x0131: "18.6.2"}, {0x9003: "2026:11:08 16:53:01"}, xmp)
    m = analyze_metadata(data, img, "JPEG")
    assert m["editing_software_detected"] == []


def test_real_photoshop_software_is_editing():
    from app.services.forensics.metadata import analyze_metadata
    data, img = _jpeg({0x0131: "Adobe Photoshop 26.0 (Windows)"}, {0x9003: "2026:11:08 16:53:01"})
    assert analyze_metadata(data, img, "JPEG")["editing_software_detected"] == ["photoshop"]


def test_xmp_edit_history_parsed():
    xmp = (b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF><rdf:Description xmp:CreatorTool="Adobe Photoshop 25.0">'
           b'<xmpMM:History><rdf:Seq><rdf:li stEvt:action="saved" stEvt:when="2026-11-10T09:00:00+01:00" '
           b'stEvt:softwareAgent="Adobe Photoshop 25.0"/></rdf:Seq></xmpMM:History></rdf:Description></rdf:RDF></x:xmpmeta>')
    data, img = _jpeg({}, {0x9003: "2026:11:01 10:00:00"}, xmp)
    t = build_timeline(data, img, "JPEG", SCAN)
    assert t["edit_history"][0]["action"] == "saved"
    assert t["creator_tool"] == "Adobe Photoshop 25.0"
    assert ids(t)["edit_history"] == "notice"
