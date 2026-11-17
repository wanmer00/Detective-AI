"""Shared definitions for the Detective AI test dataset (testing/).

The manifest starts with 50 planned placeholder cases. Images are added by hand into the category folders,
then `scan_test_dataset.py` fills the matching slots (path, SHA-256, size, dimensions). Nothing is generated.
"""
import csv
import hashlib
import os
from pathlib import Path

# DETECTIVE_TESTING_ROOT lets the tooling be smoke-tested on a throw-away copy without touching testing/.
ROOT = Path(os.environ.get("DETECTIVE_TESTING_ROOT") or Path(__file__).resolve().parents[2] / "testing")
MANIFEST = ROOT / "manifest.csv"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".avif"}

LABELS = ["REAL", "AI_GENERATED", "AI_EDITED", "MANUALLY_EDITED", "MIXED", "INCONCLUSIVE"]
FIELDS = ["image_id", "slot_status", "test_category", "planned_case", "ground_truth", "secondary_labels",
          "original_image_id", "source_group_id", "file_path", "sha256", "file_size", "width", "height", "format",
          "origin", "origin_tool", "capture_device", "transformation", "transformation_tool", "transformation_params",
          "provenance_notes", "consent_license", "include_in_metrics", "added_date"]

# code: (folder, default ground truth or "inherit", description)
CATEGORIES = {
    "C01": ("originals/C01_real_smartphone", "REAL", "Original smartphone photo, copied as a file from the phone"),
    "C02": ("originals/C02_ai_chatgpt", "AI_GENERATED", "Text-to-image generated with ChatGPT"),
    "C03": ("originals/C03_ai_gemini", "AI_GENERATED", "Text-to-image generated with Google Gemini"),
    "C04": ("derived/C04_ai_plus_photoshop", "AI_GENERATED", "AI-generated image manually edited in Photoshop"),
    "C05": ("derived/C05_real_plus_photoshop", "MANUALLY_EDITED", "Real photo edited in Photoshop with non-generative tools"),
    "C06": ("derived/C06_real_plus_genai_edit", "AI_EDITED", "Real photo modified by generative AI (inpainting, Generative Fill, object replacement)"),
    "C07": ("derived/C07_messenger", "inherit", "Sent through Telegram/WhatsApp as a photo and saved on the receiving device"),
    "C08": ("derived/C08_screenshot", "inherit", "Screenshot of a real or AI image"),
    "C09": ("derived/C09_format_resize_recompress", "inherit", "Format conversion / resize / re-compression"),
    "C10": ("derived/C10_mixed", "MIXED", "Composite with real and AI-generated elements"),
    "A01": ("derived/A01_ai_upscaling", "AI_EDITED", "Generative AI upscaling"),
    "A02": ("derived/A02_ai_filters_retouch", "AI_EDITED", "AI filters / AI retouching"),
    "A03": ("derived/A03_ai_background", "TBD", "AI background removal / replacement (label depends on what was done)"),
    "A04": ("derived/A04_screen_recapture", "inherit", "Screenshot, then photograph of the screen"),
    "A05": ("derived/A05_multi_compression", "inherit", "Multiple rounds of compression"),
    "A06": ("derived/A06_image_to_image", "AI_EDITED", "Image-to-image AI transformation (incl. 'enhance this photo' in ChatGPT)"),
    "X00": ("originals/X00_source_images", "TBD", "Extra source image used to create derivatives"),
}

# 50 planned cases: (category, slot, planned original, what to create)
PLANNED = (
    [("C01", i, None, f"Phone photo #{i}: {s}") for i, s in enumerate(
        ["person/portrait", "indoor scene", "night or low light", "landscape/outdoor", "document or text"], 1)]
    + [("C02", i, None, f"ChatGPT image #{i}: {s}") for i, s in enumerate(
        ["photorealistic person", "photorealistic street", "product photo", "illustration/art", "photorealistic food or interior"], 1)]
    + [("C03", i, None, f"Gemini image #{i}: {s}") for i, s in enumerate(
        ["photorealistic person", "photorealistic street", "product photo", "illustration/art", "photorealistic food or interior"], 1)]
    + [("C04", 1, "DA-C02-001", "Crop + colour grade in Photoshop"), ("C04", 2, "DA-C02-002", "Clone-stamp away an object"),
       ("C04", 3, "DA-C02-003", "Add text overlay"), ("C04", 4, "DA-C03-001", "Levels/curves + sharpen"),
       ("C04", 5, "DA-C03-002", "Resize + JPEG export from Photoshop")]
    + [("C05", i, f"DA-C01-00{i}", s) for i, s in enumerate(
        ["Remove an object with Clone Stamp/Healing", "Change colours / skin retouch (manual)", "Paste a region from another REAL photo",
         "Add text/sticker overlay", "Heavy crop + perspective correction"], 1)]
    + [("C06", i, f"DA-C01-00{i}", s) for i, s in enumerate(
        ["Photoshop Generative Fill: replace an object", "Inpainting in ChatGPT/Gemini: change background",
         "Remove a person with generative AI", "Generative expand of the canvas", "Replace a face/object with AI"], 1)]
    + [("C07", 1, "DA-C01-001", "Telegram, sent as photo"), ("C07", 2, "DA-C01-002", "WhatsApp, sent as photo"),
       ("C07", 3, "DA-C01-003", "Telegram, forwarded twice"), ("C07", 4, "DA-C02-004", "WhatsApp, AI image sent as photo"),
       ("C07", 5, "DA-C03-004", "Telegram, AI image sent as photo")]
    + [("C08", 1, "DA-C01-004", "Phone screenshot of a real photo in the gallery"),
       ("C08", 2, "DA-C01-005", "PC screenshot (Win+Shift+S) of a real photo"),
       ("C08", 3, "DA-C02-005", "Phone screenshot of a ChatGPT image"),
       ("C08", 4, "DA-C03-005", "PC screenshot of a Gemini image"),
       ("C08", 5, "DA-C02-001", "Screenshot of an AI image inside a chat app")]
    + [("C09", 1, "DA-C02-001", "PNG -> JPEG quality 85"), ("C09", 2, "DA-C02-002", "Convert to WEBP quality 80"),
       ("C09", 3, "DA-C02-003", "Resize to 50%"), ("C09", 4, "DA-C03-001", "Re-compress JPEG quality 60"),
       ("C09", 5, "DA-C03-002", "Resize to 1280 px + JPEG 80")]
    + [("C10", i, f"DA-C01-00{i}", s) for i, s in enumerate(
        ["Paste an AI-generated person into a real photo", "Replace the sky with an AI-generated sky",
         "Add an AI-generated object to a real scene", "Real face composited onto an AI body/background",
         "AI-generated background behind a real cut-out person"], 1)]
)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    with open(MANIFEST, encoding="utf-8-sig", newline="") as f:
        return [{k: (r.get(k) or "") for k in FIELDS} | {k: (v or "") for k, v in r.items() if k}
                for r in csv.DictReader(f)]


def write_manifest(rows: list[dict]):
    tmp = MANIFEST.with_suffix(".csv.tmp")
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    if MANIFEST.exists():
        MANIFEST.replace(MANIFEST.with_suffix(".csv.bak"))
    tmp.replace(MANIFEST)


def planned_rows() -> list[dict]:
    rows, by_id = [], {}
    for cat, slot, orig, case in PLANNED:
        rid = f"DA-{cat}-{slot:03d}"
        default = CATEGORIES[cat][1]
        gt = by_id[orig]["ground_truth"] if default == "inherit" and orig in by_id else default
        row = {k: "" for k in FIELDS}
        row |= {"image_id": rid, "slot_status": "planned", "test_category": cat, "planned_case": case,
               "ground_truth": gt, "secondary_labels": "MANUALLY_EDITED" if cat == "C04" else "",
               "original_image_id": orig or "", "source_group_id": by_id[orig]["source_group_id"] if orig in by_id else rid,
               "transformation": "none (original)" if orig is None else CATEGORIES[cat][2],
               "include_in_metrics": "yes"}
        rows.append(row)
        by_id[rid] = row
    return rows


def root_of(rid: str, by_id: dict) -> str:
    seen = set()
    while by_id.get(rid, {}).get("original_image_id") and rid not in seen:
        seen.add(rid)
        rid = by_id[rid]["original_image_id"]
    return rid
