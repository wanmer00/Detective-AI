"""Metadata & provenance forensics: EXIF, XMP/IPTC markers, PNG text chunks, C2PA presence."""
import io
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import ExifTags, Image

from app.i18n import M, render

EDIT_SOFTWARE = ["photoshop", "lightroom", "gimp", "affinity", "snapseed", "picsart", "canva", "pixelmator",
                 "paint.net", "facetune", "capture one", "luminar", "fotor", "remini", "faceapp"]
AI_EDIT_TOOLS = ["remini", "faceapp"]  # generative face enhancement / face-swap apps (output is partly AI-generated)
# keyword found in metadata -> i18n message key (text lives in frontend/src/locales/*.json)
AI_MARKERS = {
    "trainedalgorithmicmedia": "dyn.marker.iptcTrained",
    "compositewithtrainedalgorithmicmedia": "dyn.marker.iptcComposite",
    "midjourney": "dyn.marker.midjourney",
    "dall-e": "dyn.marker.dalle",
    "dalle": "dyn.marker.dalle",
    "stable diffusion": "dyn.marker.sd",
    "comfyui": "dyn.marker.comfyui",
    "novelai": "dyn.marker.novelai",
    "firefly": "dyn.marker.firefly",
    "imagen": "dyn.marker.imagen",
    "openai": "dyn.marker.openai",
    "sampler:": "dyn.marker.sampler",
    "negative prompt": "dyn.marker.prompt",
}
INTERESTING_EXIF = ["Make", "Model", "Software", "DateTime", "DateTimeOriginal", "DateTimeDigitized", "LensModel",
                    "ExposureTime", "FNumber", "ISOSpeedRatings", "FocalLength", "Artist", "Copyright",
                    "ImageDescription", "GPSInfo", "Orientation"]


def _exif(img: Image.Image) -> dict:
    out = {}
    try:
        exif = img.getexif()
        merged = dict(exif)
        try:
            merged.update(exif.get_ifd(ExifTags.IFD.Exif))
        except Exception:  # noqa: BLE001
            pass
        for tag, val in merged.items():
            name = ExifTags.TAGS.get(tag, str(tag))
            if name in INTERESTING_EXIF:
                if name == "GPSInfo":
                    out[name] = "present (coordinates withheld for privacy)"
                    continue
                if isinstance(val, bytes):
                    val = val[:64].decode("utf-8", "replace")
                out[name] = str(val)[:200]
    except Exception:  # noqa: BLE001
        pass
    return out


MAX_XMP_BYTES = 512 * 1024  # real XMP packets are a few KB; larger ones are truncated (DoS guard)


def extract_xmp(data: bytes) -> tuple[str, bool]:
    """Linear-time XMP extraction (no backtracking regex over attacker-controlled bytes).

    Returns (xmp_text, truncated)."""
    start = data.find(b"<x:xmpmeta")
    if start < 0:
        return "", False
    end = data.find(b"</x:xmpmeta>", start)
    if end < 0:
        return "", False
    end += len(b"</x:xmpmeta>")
    truncated = end - start > MAX_XMP_BYTES
    return data[start:start + min(end - start, MAX_XMP_BYTES)].decode("utf-8", "replace"), truncated


C2PA_AI_SOURCE_TYPES = {"trainedAlgorithmicMedia", "compositeWithTrainedAlgorithmicMedia", "algorithmicMedia",
                        "compositeSynthetic"}


def _c2pa(data: bytes, fmt: str) -> dict:
    """Try to read C2PA Content Credentials with c2pa-python; otherwise report raw manifest presence."""
    has_marker = b"c2pa" in data or b"jumb" in data
    result = {"present": False, "validated": False, "reader": None, "summary": None}
    try:
        import c2pa  # type: ignore

        ext = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "HEIF": ".heic", "AVIF": ".avif"}.get(fmt, ".bin")
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(data)
            tmp = f.name
        reader = None
        try:
            reader = c2pa.Reader.from_file(tmp) if hasattr(c2pa.Reader, "from_file") else c2pa.Reader(tmp)
            manifest = json.loads(reader.json())
            active = manifest.get("active_manifest")
            m = manifest.get("manifests", {}).get(active, {})
            # digitalSourceType declared in the signed c2pa.actions assertion, e.g. ".../trainedAlgorithmicMedia"
            source_types = sorted({
                str(ac.get("digitalSourceType", "")).rsplit("/", 1)[-1]
                for a in m.get("assertions", []) if str(a.get("label", "")).startswith("c2pa.actions")
                for ac in (a.get("data") or {}).get("actions", []) or [] if ac.get("digitalSourceType")})
            generator = m.get("claim_generator") or ((m.get("claim_generator_info") or [{}])[0].get("name"))
            try:  # "Valid" = signature and content hashes intact; "Trusted" = signer on a loaded trust list
                state = str(reader.get_validation_state())
            except Exception:  # noqa: BLE001
                state = "Unknown"
            issues = [v.get("code") for v in manifest.get("validation_status") or []]
            intact = state.lower() in ("valid", "trusted")
            declared = any(t in C2PA_AI_SOURCE_TYPES for t in source_types)
            result.update(present=True, reader="c2pa-python", validated=intact,
                          summary={"claim_generator": generator,
                                   "title": m.get("title"),
                                   "issuer": (m.get("signature_info") or {}).get("issuer"),
                                   "digital_source_types": source_types,
                                   "validation_state": state,
                                   "signer_trusted": state.lower() == "trusted",
                                   "ai_declared": declared and intact,
                                   "ai_declared_but_invalid": declared and not intact,
                                   "validation_issues": issues})
        finally:
            if reader is not None and hasattr(reader, "close"):
                try:
                    reader.close()  # Windows: the reader keeps the file open; close before deleting
                except Exception:  # noqa: BLE001
                    pass
            try:
                Path(tmp).unlink(missing_ok=True)
            except OSError:
                pass  # never let temp-file cleanup hide a successfully read manifest
    except ImportError:
        result.update(present=has_marker, reader="byte-signature scan (c2pa-python not installed)")
    except Exception:  # noqa: BLE001 - no manifest or unreadable
        result.update(present=False, reader="c2pa-python")
        if has_marker:
            result["summary"] = {"note": "C2PA/JUMBF bytes found but manifest could not be parsed or validated"}
    return result


def _exiftool(data: bytes, fmt: str) -> dict | None:
    exe = shutil.which("exiftool")
    if not exe:
        return None
    ext = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "HEIF": ".heic", "AVIF": ".avif"}.get(fmt, ".bin")
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(data)
        tmp = f.name
    try:
        r = subprocess.run([exe, "-j", "-G", "-n", tmp], capture_output=True, timeout=15, check=False)
        meta = json.loads(r.stdout or b"[{}]")[0]
        meta.pop("SourceFile", None)
        return {k: v for k, v in meta.items() if not k.startswith(("System:", "File:Directory", "File:FileName"))}
    except Exception:  # noqa: BLE001
        return None
    finally:
        Path(tmp).unlink(missing_ok=True)


def analyze_metadata(data: bytes, img: Image.Image, fmt: str) -> dict:
    exif = _exif(img)
    png_text = {}
    if fmt == "PNG":
        for k, v in (img.info or {}).items():
            if isinstance(v, str):
                png_text[k] = v[:500]
    xmp, xmp_truncated = extract_xmp(data)
    haystack = " ".join([json.dumps(exif), json.dumps(png_text), xmp]).lower()

    marker_msgs = [M(key) for key in sorted({key for kw, key in AI_MARKERS.items() if kw in haystack})]
    c2pa_info = _c2pa(data, fmt)
    cs = c2pa_info.get("summary") or {}
    if cs.get("ai_declared"):
        marker_msgs.append(M("dyn.marker.c2pa", types=", ".join(cs.get("digital_source_types", [])),
                             generator=cs.get("claim_generator") or "?", issuer=cs.get("issuer") or "?",
                             trust=M("dyn.marker.c2paTrusted" if cs.get("signer_trusted") else "dyn.marker.c2paUntrusted")))
    ai_markers = [render(m) for m in marker_msgs]
    software = exif.get("Software", "")
    xmp_tool = re.search(r'CreatorTool="([^"]{1,300})"|<xmp:CreatorTool>([^<]{1,300})<', xmp)
    if xmp_tool:
        software = software or (xmp_tool.group(1) or xmp_tool.group(2))
    # Only fields that name the writing application count as editing evidence. Searching the whole XMP text
    # would match namespace prefixes such as `photoshop:DateCreated`, which iPhones and cameras write too.
    agents = re.findall(r'softwareAgent="([^"]{1,300})"|<stEvt:softwareAgent>([^<]{1,300})<', xmp)[:500]
    tool_fields = [exif.get("Software", ""), *(a or b for a, b in agents),
                   (xmp_tool.group(1) or xmp_tool.group(2)) if xmp_tool else "",
                   *(v for k, v in png_text.items() if k.lower() in ("software", "creator", "comment", "description"))]
    tool_text = " ".join(tool_fields).lower()
    edit_hits = sorted({s for s in EDIT_SOFTWARE if s in tool_text})
    has_history = "photoshop:history" in haystack or "stevt:" in haystack or "xmpmm:history" in haystack
    # A photo that was partly generated/altered by AI: IPTC/C2PA "composite with trained algorithmic media",
    # or a generative enhancement / face-swap app named in a tool field.
    composite = "compositewithtrainedalgorithmicmedia" in haystack or (
        bool(cs.get("ai_declared")) and "compositeWithTrainedAlgorithmicMedia" in (cs.get("digital_source_types") or []))
    ai_edit_tools = sorted({s for s in AI_EDIT_TOOLS if s in tool_text})

    return {
        "exif": exif,
        "exif_present": bool(exif),
        "camera": {"make": exif.get("Make"), "model": exif.get("Model"), "lens": exif.get("LensModel")}
        if exif.get("Make") or exif.get("Model") else None,
        "capture_settings_present": any(k in exif for k in ("ExposureTime", "FNumber", "ISOSpeedRatings", "FocalLength")),
        "software": software or None,
        "editing_software_detected": edit_hits,
        "edit_history_in_xmp": has_history,
        "ai_composite_declared": composite,
        "ai_edit_tools": ai_edit_tools,
        "xmp_present": bool(xmp),
        "xmp_truncated": xmp_truncated,
        "png_text_chunks": png_text,
        "ai_generation_markers": ai_markers,
        "ai_generation_marker_msgs": marker_msgs,
        "c2pa": c2pa_info,
        "exiftool": _exiftool(data, fmt),
    }
