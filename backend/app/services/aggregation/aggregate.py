"""Transparent rule-based evidence aggregation.

Scores are NOT averaged and scores from different models are never compared on one scale. Every detector
makes its own decision with its own published rule (SwinV2: 7-view median >= 0.80 / <= 0.20; Community
Forensics: raw logit vs. the author's boundary). Detectors are grouped into FAMILIES of related models
(models fine-tuned from one another are not independent evidence); a family casts one vote only when its
members agree. The verdict is derived from explicit rules that are returned verbatim in the report.
All human-readable text is emitted as i18n message objects (`*_msgs`, `msg`) plus an English rendering.
"""
from app.core.config import settings
from app.i18n import M, item, render

VERDICTS = {
    "ai_likely": "Likely AI-generated",
    "ai_edited": "Likely AI-edited photograph",
    "authentic_likely": "Likely authentic photograph",
    "not_ai": "No AI generation detected",
    "manipulated_possible": "Potential manipulation / editing",
    "inconclusive": "Inconclusive",
}
HIGH, LOW = 0.80, 0.20
MODEL_INPUT_PX = 256  # SwinV2 detector input size
REC_COUNT = {"ai_likely": 3, "ai_edited": 3, "authentic_likely": 2, "not_ai": 3, "manipulated_possible": 2, "inconclusive": 3}
FAMILY_NAMES = {"swinv2": "SwinV2", "community_forensics": "Community Forensics"}


def _band(score: float) -> str:
    if score >= 0.9:
        return "very high"
    if score >= HIGH:
        return "high"
    if score >= 0.6:
        return "elevated"
    if score > 0.4:
        return "uncertain"
    if score > LOW:
        return "low"
    return "very low"


def _band_msg(score: float) -> dict:
    return M("band." + _band(score).replace(" ", "_"))


def decision(d: dict) -> str:
    """The detector's own decision: ai | real | uncertain | unreliable."""
    if d.get("decision"):
        return d["decision"]
    if d.get("stable") is False:
        return "unreliable"
    s = d["positive_score"]
    return "ai" if s >= HIGH else "real" if s <= LOW else "uncertain"


def family_votes(ok: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for d in ok:
        groups.setdefault(d.get("family") or d.get("key") or d["model"], []).append(d)
    out = []
    for fam, members in groups.items():
        decs = [decision(m) for m in members]
        vote = decs[0] if len(set(decs)) == 1 and decs[0] in ("ai", "real") else "uncertain"
        out.append({"family": fam, "name": FAMILY_NAMES.get(fam, members[0].get("name") or members[0]["model"]),
                    "vote": vote, "split": "ai" in decs and "real" in decs,
                    "members": [{"key": m.get("key"), "name": m.get("name") or m["model"], "model": m["model"],
                                 "decision": decision(m), "score": m["positive_score"],
                                 "score_kind": m.get("score_kind", "raw"), "threshold": m.get("threshold")}
                                for m in members]})
    return out


def image_quality(signal: dict) -> dict:
    W, H = signal.get("width", 0), signal.get("height", 0)
    q = (signal.get("jpeg") or {}).get("estimated_quality")
    reasons = []
    if 0 < max(W, H) < settings.low_quality_long_side:
        reasons.append("small")
    if q is not None and q <= settings.low_quality_jpeg:
        reasons.append("compressed")
    return {"long_side": max(W, H), "jpeg_quality": q, "low_quality": bool(reasons), "reasons": reasons,
            "min_long_side": settings.low_quality_long_side, "max_jpeg_quality": settings.low_quality_jpeg}


def _member_msg(m: dict) -> dict:
    return M("dyn.ev.member", name=m["name"], decision=M(f"decision.{m['decision']}"), score=f"{m['score']:.2f}")


def aggregate(detectors: list[dict], meta: dict, signal: dict, faces: dict, timeline: dict | None = None) -> dict:
    ev_for, ev_against, ev_edit, rules, lims = [], [], [], [], []
    ok = [d for d in detectors if d["status"] == "ok"]
    fams = family_votes(ok)
    quality = image_quality(signal)

    # ---- Detector evidence (one entry per family; single-model families keep their per-model wording) ----
    if not ok:
        lims.append(M("dyn.lim.noDetector"))
    W, H = signal.get("width", 0), signal.get("height", 0)
    crop_px = min(W, H) // 2
    small = 0 < min(W, H) < 2 * MODEL_INPUT_PX  # SwinV2 half-image views fall below the model's input size
    for f in fams:
        if len(f["members"]) > 1:
            members = [_member_msg(m) for m in f["members"]]
            msg = M("dyn.ev.family", family=f["name"], n=len(members), members=members)
            if f["vote"] == "ai":
                ev_for.append(item("moderate", "detector", msg))
            elif f["vote"] == "real":
                ev_against.append(item("moderate", "detector", msg))
            else:
                lims.append(M("dyn.lim.familySplit" if f["split"] else "dyn.lim.familyUncertain", family=f["name"], members=members))
            continue
        d = next(x for x in ok if (x.get("family") or x.get("key") or x["model"]) == f["family"])
        s, dec = d["positive_score"], decision(d)
        if dec == "unreliable":
            views = [M("dyn.lim.viewScore", view=M(f"views.{k}"), score=f"{v:.2f}") for k, v in (d.get("view_scores") or {}).items()]
            cause = M("dyn.lim.unstableCause", w=W, h=H, crop=crop_px, input=MODEL_INPUT_PX) if small else ""
            lims.append(M("dyn.lim.unstable", model=d["model"], views=views, cause=cause))
            continue
        if d.get("score_kind", "raw") == "raw":
            msg = M("dyn.ev.detectorScore", model=d["model"], score=f"{s:.2f}", band=_band_msg(s))
            strong = s >= 0.9 if dec == "ai" else s <= 0.1
        else:
            msg = M("dyn.ev.detectorDecision", model=d["model"], decision=M(f"decision.{dec}"), score=f"{s:.2f}")
            strong = False
        if dec == "ai":
            ev_for.append(item("strong" if strong else "moderate", "detector", msg))
        elif dec == "real":
            ev_against.append(item("strong" if strong else "moderate", "detector", msg))
        else:
            lims.append(M("dyn.lim.uncertainScore", model=d["model"], score=f"{s:.2f}"))
    ai_f = [f for f in fams if f["vote"] == "ai"]
    real_f = [f for f in fams if f["vote"] == "real"]
    decided = ai_f + real_f
    conflict = bool(ai_f and real_f)
    split = any(f["split"] for f in fams)
    if len(fams) == 1:
        lims.append(M("dyn.lim.singleDetector"))
    if conflict:
        lims.append(M("dyn.lim.disagree"))

    # ---- Metadata evidence -------------------------------------------------
    markers = meta.get("ai_generation_marker_msgs") or meta["ai_generation_markers"]
    if meta["ai_generation_markers"]:
        ev_for.append(item("strong", "metadata", M("dyn.ev.markers", markers=markers)))
    if meta.get("ai_edit_tools"):
        ev_for.append(item("strong", "metadata", M("dyn.ev.aiEditTool", tools=", ".join(meta["ai_edit_tools"]))))
    c2pa = meta["c2pa"]
    cs = c2pa.get("summary") or {}
    if c2pa.get("present") and not cs.get("ai_declared"):
        gen = cs.get("claim_generator")
        ev_against.append(item("moderate", "provenance", M("dyn.ev.c2paPresentGen", gen=gen) if gen else M("dyn.ev.c2paPresent")))
    if meta["camera"] and meta["capture_settings_present"]:
        cam = f"{meta['camera'].get('make') or ''} {meta['camera'].get('model') or ''}".strip()
        ev_against.append(item("weak", "metadata", M("dyn.ev.cameraExif", camera=cam)))
    elif meta["camera"]:
        ev_against.append(item("weak", "metadata", M("dyn.ev.cameraMake")))
    if not meta["exif_present"]:
        lims.append(M("dyn.lim.noExif"))
    if meta["editing_software_detected"]:
        ev_edit.append(item("moderate", "metadata", M("dyn.ev.editSoftware", tools=", ".join(meta["editing_software_detected"]))))
    if meta["edit_history_in_xmp"]:
        ev_edit.append(item("moderate", "metadata", M("dyn.ev.xmpHistory")))

    for c in (timeline or {}).get("checks", []):
        if c["status"] == "warning":
            ev_edit.append(item("moderate", "timeline", M("dyn.ev.timeline", title=c.get("title_msg") or c["title"],
                                                          detail=c.get("detail_msg") or c["detail"])))

    # ---- Signal evidence (weak by design) ----------------------------------
    ela = signal.get("ela") or {}
    if ela.get("block_nonuniformity", 0) > 1.2 and signal.get("format") == "JPEG":
        ev_edit.append(item("weak", "ela", M("dyn.ev.ela", value=ela["block_nonuniformity"])))
    jq = signal.get("jpeg")
    if jq and jq["estimated_quality"] < 70:
        lims.append(M("dyn.lim.lowJpeg", q=jq["estimated_quality"]))
    if cs.get("ai_declared_but_invalid"):
        lims.append(M("dyn.lim.c2paInvalid", issues=", ".join(cs.get("validation_issues") or [cs.get("validation_state", "?")])))
    elif cs.get("ai_declared") and not cs.get("signer_trusted"):
        lims.append(M("dyn.lim.c2paUntrusted"))
    if meta.get("xmp_truncated"):
        lims.append(M("dyn.lim.xmpTruncated"))
    if small:
        lims.append(M("dyn.lim.smallImage", w=W, h=H))

    # ---- Face evidence -----------------------------------------------------
    flagged = [f for f in faces.get("faces", []) if f.get("flagged")]
    if flagged:
        ev_edit.append(item("moderate", "face", M("dyn.ev.facesFlagged", n=len(flagged), ids=", ".join(str(f["id"]) for f in flagged))))
    elif faces.get("face_count"):
        scored = [f for f in faces["faces"] if f.get("manipulation_score") is not None]
        if scored:
            ev_against.append(item("weak", "face", M("dyn.ev.facesClean", n=len(scored))))

    # ---- Rules -------------------------------------------------------------
    strong_for = [e for e in ev_for if e["strength"] == "strong"]
    strong_edit = any(e["strength"] != "weak" for e in ev_edit)
    camera = bool(meta["camera"] and meta["capture_settings_present"])
    ai_edit_meta = bool(meta.get("ai_composite_declared") or meta.get("ai_edit_tools"))

    def lone_family_ok(f):
        # With one family only, a raw-score detector must clear the stricter 0.90 bar (as before multi-family voting).
        return all(m["score_kind"] != "raw" or m["score"] >= 0.9 for m in f["members"])

    verdict = "inconclusive"
    if ai_edit_meta:
        verdict = "ai_edited"
        rules.append("R1e")
    elif meta["ai_generation_markers"]:
        verdict = "ai_likely"
        rules.append("R1")
    elif ai_f and not real_f and (len(fams) >= 2 or lone_family_ok(ai_f[0])):
        # P7 in scripts/simulate_policies.py: one family says AI and no family says not-AI.
        if camera:
            verdict = "ai_edited"  # camera capture EXIF + AI pixels: an AI-edited photo (or AI image with copied EXIF)
            rules.append("R2e")
        else:
            verdict = "ai_likely"
            rules.append("R2")
    elif real_f and not ai_f:
        if strong_edit:
            verdict = "manipulated_possible"
            rules.append("R3")
        elif camera:
            verdict = "authentic_likely"
            rules.append("R4")
        elif quality["low_quality"]:
            # Detector recall drops on small / heavily compressed files (benchmark: SwinV2 recall 0.58 -> 0.44 at
            # 320 px). Without provenance, "no AI detected" would be a confident claim from weak evidence.
            rules.append("R9")
            lims.append(M("dyn.lim.qualityGate", side=quality["long_side"],
                          q=quality["jpeg_quality"] if quality["jpeg_quality"] is not None else "—",
                          min_side=quality["min_long_side"], max_q=quality["max_jpeg_quality"]))
        else:
            # Without provenance we can only say the image does not look generated. AI detectors are blind to
            # Photoshop composites, overlays and splices, so "authentic" would overclaim.
            verdict = "not_ai"
            rules.append("R4b")
    elif (camera and real_f and not meta["editing_software_detected"] and not meta["edit_history_in_xmp"]
          and not strong_edit):
        # Generators do not write camera make/model + exposure EXIF. Requires at least one detector family to agree
        # the content is camera-like, so forged EXIF on an image all detectors flag does not pass.
        verdict = "authentic_likely"
        rules.append("R8")
    elif conflict:
        rules.append("R7")
    elif strong_edit and not ai_f:
        verdict = "manipulated_possible"
        rules.append("R5")
    else:
        rules.append("R6")

    # ---- Evidence strength & detection confidence -------------------------
    if verdict == "inconclusive":
        strength = "insufficient"
    elif verdict in ("ai_likely", "ai_edited") and (meta["ai_generation_markers"] or ai_edit_meta or (len(ai_f) >= 2 and strong_for)):
        strength = "strong"
    elif len(decided) >= 2 and not conflict:
        strength = "moderate"
    else:
        strength = "limited"

    # Detection confidence = how much the independent detector families agree. It is NOT a probability.
    if not ok:
        level = "none"
    elif conflict:
        level = "conflict"
    elif not decided:
        level = "none"
    elif len(decided) >= 2 and len(decided) == len(fams):
        level = "high"
    elif len(fams) >= 2:
        level = "moderate"
    else:
        level = "limited"
    direction = "ai" if ai_f and not real_f else "real" if real_f and not ai_f else None
    confidence = {"level": level, "direction": direction, "agreeing": len(ai_f) if direction == "ai" else len(real_f) if direction == "real" else 0,
                  "families": len(fams)}

    # A headline score is only shown when every available detector reports on the same raw scale and agrees;
    # it is the least confident agreeing detector (conservative bound), never an average. Mixed scales -> none.
    likelihood = None
    if ok and all(d.get("score_kind", "raw") == "raw" for d in ok):
        high = [d for d in ok if decision(d) == "ai"]
        low = [d for d in ok if decision(d) == "real"]
        if len(high) == len(ok):
            likelihood = min(d["positive_score"] for d in ok)
        elif len(low) == len(ok):
            likelihood = max(d["positive_score"] for d in ok)
        elif len(ok) == 1 and ok[0].get("stable", True):
            likelihood = ok[0]["positive_score"]
    unreliable = any(decision(d) == "unreliable" for d in ok)
    agreement = ("no detectors" if not ok else "disagree" if conflict
                 else ("agree: AI" if direction == "ai" else "agree: not AI") if decided and len(decided) == len(fams)
                 else ("partial: AI" if direction == "ai" else "partial: not AI") if decided
                 else "unstable" if unreliable else "uncertain")

    if any(d.get("score_kind") == "vendor_calibrated" for d in ok):
        lims.append(M("dyn.lim.vendorCalibrated"))
    rec_msgs = [M(f"dyn.rec.{verdict}.{i}") for i in range(1, REC_COUNT[verdict] + 1)]
    lims += [M("dyn.lim.noEditDetection"), M("dyn.lim.notCalibrated"), M("dyn.lim.evasion")]
    rule_msgs = [M(f"dyn.rule.{r}") for r in rules]
    method = M("dyn.method")

    return {
        "verdict": verdict,
        "verdict_label": VERDICTS[verdict],
        "ai_likelihood": likelihood,
        "ai_likelihood_band": _band(likelihood) if likelihood is not None else None,
        "detection_confidence": confidence,
        "evidence_strength": strength,
        "detectors_available": len(ok),
        "detectors_total": len(detectors),
        "detector_families": fams,
        "detectors_disagree": conflict or split,
        "family_conflict": conflict,
        "family_split": split,
        "detector_agreement": agreement,
        "unstable_reason": "low_resolution" if agreement == "unstable" and small else ("unknown" if agreement == "unstable" else None),
        "low_resolution": small,
        "image_quality": quality,
        "ai_votes": len(ai_f),
        "not_ai_votes": len(real_f),
        "evidence_for_ai": ev_for,
        "evidence_against_ai": ev_against,
        "manipulation_indicators": ev_edit,
        "rules": rules,
        "rules_fired": [render(m) for m in rule_msgs],
        "rules_msgs": rule_msgs,
        "limitations": [render(m) for m in lims],
        "limitations_msgs": lims,
        "recommendations": [render(m) for m in rec_msgs],
        "recommendations_msgs": rec_msgs,
        "method": render(method),
        "method_msg": method,
    }
