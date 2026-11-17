"""Detected-signals list: one entry per independent forensic signal, shown separately in the UI and report.

status values:
  points_ai        - the signal leans towards AI generation
  points_camera    - the signal leans towards a camera original
  points_edit      - the signal indicates processing/editing
  neutral          - measured, but does not lean either way
  unreliable       - measured, but the measurement itself is not trustworthy on this image
  unavailable      - could not be measured
No signal carries a probability; `value` is always the raw measurement. Text is emitted as i18n messages
(`name_msg`, `value_msg`, `finding_msg`, `meaning_msg`) plus an English rendering.
"""
from app.core.config import settings
from app.i18n import M, render
from app.services.aggregation.aggregate import decision

MESSENGER_SIDES = {800, 960, 1024, 1080, 1200, 1280, 1440, 1600, 2048, 2560}
GENERATOR_SIDES = {512, 576, 640, 704, 768, 832, 896, 960, 1024, 1088, 1152, 1216, 1280, 1344, 1408, 1536, 1792, 2048}
GROUPS = {"ai": "AI generation", "provenance": "Provenance", "processing": "Processing", "compression": "Compression",
          "properties": "Image properties", "faces": "Faces"}


def build_signals(detectors, meta, sig, faces, timeline, file) -> list[dict]:
    out = []

    def add(sid, group, name, status, value, finding, meaning, strength="weak"):
        """value: raw string (not translated) or a message; name/finding/meaning: messages."""
        out.append({"id": sid, "group": GROUPS[group], "group_key": group, "status": status, "strength": strength,
                    "name": render(name), "name_msg": name,
                    "value": render(value) if value is not None else None,
                    "value_msg": value if isinstance(value, dict) else None,
                    "finding": render(finding), "finding_msg": finding,
                    "meaning": render(meaning), "meaning_msg": meaning})

    S = "dyn.sig."
    # 1. AI detector(s): each uses its own decision rule; vendor-calibrated scores are labelled as such
    for d in detectors:
        name = M(S + "ai.name", model=d["model"])
        if d["status"] != "ok":
            add(f"ai_{d['key']}", "ai", name, "unavailable", None, M(S + "ai.unavailableFinding"), M(S + "ai.unavailableMeaning"))
            continue
        s, dec = d["positive_score"], decision(d)
        raw = d.get("score_kind", "raw") == "raw"
        value = f"{s:.3f}" if raw else M(S + "ai.calValue", score=f"{s:.3f}", logit=f"{d.get('raw_logit', 0):.2f}")
        if dec == "unreliable":
            small = M(S + "ai.unreliableSmall", w=file["width"], h=file["height"]) if min(file["width"], file["height"]) < 512 else ""
            add(f"ai_{d['key']}", "ai", name, "unreliable",
                M(S + "ai.unreliableValue", median=f"{s:.2f}", pct=int(d["stability"] * 100)),
                M(S + "ai.unreliableFinding", small=small), M(S + "ai.unreliableMeaning"))
        elif dec == "ai":
            add(f"ai_{d['key']}", "ai", name, "points_ai", value, M(S + ("ai.aiFinding" if raw else "ai.cfAiFinding")),
                M(S + "ai.aiMeaning"), "strong" if raw and s >= 0.95 else "moderate")
        elif dec == "real":
            add(f"ai_{d['key']}", "ai", name, "points_camera", value, M(S + ("ai.camFinding" if raw else "ai.cfCamFinding")),
                M(S + "ai.camMeaning"), "moderate")
        else:
            add(f"ai_{d['key']}", "ai", name, "neutral", value, M(S + "ai.neutralFinding"), M(S + "ai.neutralMeaning"))

    # 1b. Image quality for detection (drives the quality gate in aggregate.py)
    long_side, q = max(file["width"], file["height"]), (sig.get("jpeg") or {}).get("estimated_quality")
    low = long_side < settings.low_quality_long_side or (q is not None and q <= settings.low_quality_jpeg)
    add("image_quality", "properties", M(S + "quality.name"), "unreliable" if low else "neutral",
        M(S + "quality.value", side=long_side, q=f"~{q}" if q is not None else "—"),
        M(S + ("quality.lowFinding" if low else "quality.okFinding"), min_side=settings.low_quality_long_side,
          max_q=settings.low_quality_jpeg),
        M(S + ("quality.lowMeaning" if low else "quality.okMeaning")), "moderate" if low else "weak")

    # 2. Generator metadata
    if meta["ai_generation_markers"]:
        add("meta_ai_markers", "provenance", M(S + "markers.name"), "points_ai",
            "; ".join(meta["ai_generation_markers"]), M(S + "markers.foundFinding"), M(S + "markers.foundMeaning"), "strong")
        out[-1]["value_msg"] = meta.get("ai_generation_marker_msgs")  # list of messages, rendered with "; "
    else:
        add("meta_ai_markers", "provenance", M(S + "markers.name"), "neutral", M(S + "markers.noneValue"),
            M(S + "markers.noneFinding"), M(S + "markers.noneMeaning"))

    # 3. C2PA
    c2 = meta["c2pa"]
    cs = c2.get("summary") or {}
    if c2.get("present") and cs.get("ai_declared"):
        add("c2pa", "provenance", M(S + "c2pa.name"), "points_ai",
            f"{cs.get('claim_generator') or 'signed'}: {', '.join(cs.get('digital_source_types', []))}",
            M(S + "c2pa.aiFinding"), M(S + "c2pa.aiMeaning"), "strong")
    elif c2.get("present"):
        gen = cs.get("claim_generator")
        add("c2pa", "provenance", M(S + "c2pa.name"), "neutral", gen or M(S + "c2pa.presentValue"),
            M(S + "c2pa.presentFinding"), M(S + "c2pa.presentMeaning"), "strong")
    else:
        add("c2pa", "provenance", M(S + "c2pa.name"), "neutral", M(S + "c2pa.absentValue"),
            M(S + "c2pa.absentFinding"), M(S + "c2pa.absentMeaning"))

    # 4. Camera provenance
    cam = meta["camera"]
    cam_txt = " ".join(filter(None, [cam.get("make"), cam.get("model")])) if cam else ""
    if cam and meta["capture_settings_present"]:
        add("camera_exif", "provenance", M(S + "camera.name"), "points_camera", cam_txt,
            M(S + "camera.fullFinding"), M(S + "camera.fullMeaning"), "moderate")
    elif cam:
        add("camera_exif", "provenance", M(S + "camera.name"), "points_camera", cam_txt,
            M(S + "camera.partFinding"), M(S + "camera.partMeaning"))
    else:
        add("camera_exif", "provenance", M(S + "camera.name"), "neutral", M(S + "camera.absentValue"),
            M(S + "camera.absentFinding"), M(S + "camera.absentMeaning"))

    # 5. Editing software
    edit = meta["editing_software_detected"]
    if edit or meta["edit_history_in_xmp"]:
        add("edit_software", "processing", M(S + "edit.name"), "points_edit",
            ", ".join(edit) if edit else M(S + "edit.historyValue"),
            M(S + "edit.foundFinding", tools=", ".join(edit) if edit else M(S + "edit.historyTools")),
            M(S + "edit.foundMeaning"), "moderate")
    else:
        sw = meta["software"]
        add("edit_software", "processing", M(S + "edit.name"), "neutral", sw or M(S + "edit.noneValue"),
            M(S + "edit.noneFinding", sw=M(S + "edit.noneSw", sw=sw) if sw else ""), M(S + "edit.noneMeaning"))

    # 6. Timeline consistency
    warns = [c for c in timeline["checks"] if c["status"] == "warning"]
    if warns:
        add("timeline", "processing", M(S + "timeline.name"), "points_edit", M(S + "timeline.warnValue", n=len(warns)),
            [c.get("title_msg") or c["title"] for c in warns], M(S + "timeline.warnMeaning"), "moderate")
    elif timeline["embedded_count"]:
        add("timeline", "processing", M(S + "timeline.name"), "neutral", M(S + "timeline.okValue", n=timeline["embedded_count"]),
            M(S + "timeline.okFinding"), M(S + "timeline.okMeaning"))
    else:
        add("timeline", "processing", M(S + "timeline.name"), "unavailable", M(S + "timeline.noneValue"),
            M(S + "timeline.noneFinding"), M(S + "timeline.noneMeaning"))

    # 7. Compression history
    jq = sig.get("jpeg")
    if jq:
        q = jq["estimated_quality"]
        add("jpeg_quality", "compression", M(S + "jpeg.name"), "neutral", f"~{q}", M(S + "jpeg.finding", q=q), M(S + "jpeg.meaning"))
    else:
        add("jpeg_quality", "compression", M(S + "jpeg.name"), "unavailable", file["format"],
            M(S + "jpeg.naFinding"), M(S + "jpeg.naMeaning"))

    sides = {file["width"], file["height"]}
    if jq and not meta["exif_present"] and max(sides) in MESSENGER_SIDES and 65 <= jq["estimated_quality"] <= 90:
        add("reshare", "compression", M(S + "reshare.name"), "neutral",
            M(S + "reshare.value", w=file["width"], h=file["height"], q=jq["estimated_quality"]),
            M(S + "reshare.finding"), M(S + "reshare.meaning"))

    dims = f"{file['width']}×{file['height']}"
    if not meta["exif_present"] and all(s in GENERATOR_SIDES for s in sides) and all(s % 64 == 0 for s in sides):
        add("dimensions", "properties", M(S + "dims.name"), "neutral", dims, M(S + "dims.genFinding"), M(S + "dims.genMeaning"))
    else:
        add("dimensions", "properties", M(S + "dims.name"), "neutral", dims, M(S + "dims.finding"), M(S + "dims.meaning"))

    # 8. ELA
    ela = sig.get("ela") or {}
    if ela:
        nu = ela.get("block_nonuniformity", 0)
        status = "points_edit" if nu > 1.2 and file["format"] == "JPEG" else "neutral"
        add("ela", "compression", M(S + "ela.name"), status, M(S + "ela.value", nu=nu),
            M(S + ("ela.unevenFinding" if status == "points_edit" else "ela.evenFinding")), M(S + "ela.meaning"))

    # 9. Faces
    if faces.get("status") == "ok" and faces.get("face_count"):
        flagged = [f for f in faces["faces"] if f.get("flagged")]
        scored = [f["manipulation_score"] for f in faces["faces"] if f.get("manipulation_score") is not None]
        n = faces["face_count"]
        add("faces", "faces", M(S + "faces.name"), "points_edit" if flagged else "neutral",
            M(S + "faces.valueMax", n=n, max=f"{max(scored):.2f}") if scored else M(S + "faces.value", n=n),
            M(S + "faces.flaggedFinding", n=len(flagged)) if flagged else M(S + "faces.okFinding"), M(S + "faces.meaning"))
    elif faces.get("status") == "ok":
        add("faces", "faces", M(S + "faces.name"), "neutral", M(S + "faces.noneValue"),
            M(S + "faces.noneFinding"), M(S + "faces.noneMeaning"))
    return out
