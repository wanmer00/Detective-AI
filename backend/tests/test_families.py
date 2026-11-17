"""Multi-family detector voting, quality gate and AI-edited verdict (aggregate.py)."""
from app.services.aggregation.aggregate import aggregate
from tests.test_aggregation import FACES, META, SIG

BIG = {**SIG, "width": 1600, "height": 1200}
SMALL = {**SIG, "format": "JPEG", "width": 320, "height": 179, "jpeg": {"estimated_quality": 85}}
COMPRESSED = {**SIG, "format": "JPEG", "width": 1600, "height": 1200, "jpeg": {"estimated_quality": 70}}


def swin(score, stable=True):
    dec = "unreliable" if not stable else "ai" if score >= 0.8 else "real" if score <= 0.2 else "uncertain"
    return {"key": "swinv2_ai_detector", "model": "haywoodsloan/ai-image-detector-deploy", "name": "SwinV2", "family": "swinv2",
            "status": "ok", "positive_score": score, "stable": stable, "decision": dec, "score_kind": "raw"}


def cf(key, p, dec):
    return {"key": key, "model": f"Thermostatic/{key}", "name": key, "family": "community_forensics", "status": "ok",
            "positive_score": p, "stable": True, "decision": dec, "score_kind": "vendor_calibrated"}


def run(dets, sig=BIG, meta=META):
    return aggregate(dets, meta, sig, FACES)


def test_related_models_are_one_vote_and_split_means_no_vote():
    a = run([swin(0.5), cf("cf_frontier", 0.2, "real"), cf("cf_lowq", 0.71, "ai")])
    fam = {f["family"]: f for f in a["detector_families"]}
    assert fam["community_forensics"]["vote"] == "uncertain" and fam["community_forensics"]["split"]
    assert a["verdict"] == "inconclusive" and a["family_split"] and not a["family_conflict"]


def test_cf_family_ai_with_uncertain_swinv2_is_ai():
    a = run([swin(0.5), cf("cf_frontier", 0.9, "ai"), cf("cf_lowq", 0.8, "ai")])
    assert a["verdict"] == "ai_likely" and a["rules"] == ["R2"] and a["detection_confidence"]["level"] == "moderate"


def test_families_contradicting_is_inconclusive_r7():
    a = run([swin(0.02), cf("cf_frontier", 0.9, "ai"), cf("cf_lowq", 0.8, "ai")])
    assert a["verdict"] == "inconclusive" and a["rules"] == ["R7"] and a["family_conflict"]
    assert a["detection_confidence"]["level"] == "conflict"


def test_both_families_real_on_good_image_is_not_ai_high_confidence():
    a = run([swin(0.02), cf("cf_frontier", 0.1, "real"), cf("cf_lowq", 0.2, "real")])
    assert a["verdict"] == "not_ai" and a["detection_confidence"] == {"level": "high", "direction": "real", "agreeing": 2, "families": 2}


def test_quality_gate_small_image_never_claims_not_ai():
    a = run([swin(0.01), cf("cf_frontier", 0.1, "real"), cf("cf_lowq", 0.2, "real")], SMALL)
    assert a["verdict"] == "inconclusive" and a["rules"] == ["R9"] and a["image_quality"]["reasons"] == ["small"]


def test_quality_gate_heavy_jpeg():
    a = run([swin(0.01), cf("cf_frontier", 0.1, "real"), cf("cf_lowq", 0.2, "real")], COMPRESSED)
    assert a["verdict"] == "inconclusive" and a["image_quality"]["reasons"] == ["compressed"]


def test_quality_gate_does_not_block_ai_verdict():
    a = run([swin(0.95), cf("cf_frontier", 0.9, "ai"), cf("cf_lowq", 0.8, "ai")], SMALL)
    assert a["verdict"] == "ai_likely"


def test_quality_gate_does_not_override_camera_provenance():
    m = {**META, "exif_present": True, "camera": {"make": "Apple", "model": "iPhone 15"}, "capture_settings_present": True}
    assert run([swin(0.01), cf("cf_frontier", 0.1, "real"), cf("cf_lowq", 0.2, "real")], SMALL, m)["verdict"] == "authentic_likely"


def test_mixed_score_scales_give_no_headline_probability():
    a = run([swin(0.95), cf("cf_frontier", 0.9, "ai"), cf("cf_lowq", 0.8, "ai")])
    assert a["ai_likelihood"] is None and a["detection_confidence"]["level"] == "high"
    assert any("not validated" in x for x in a["limitations"])


def test_composite_metadata_is_ai_edited():
    m = {**META, "ai_generation_markers": ["IPTC composite"], "ai_composite_declared": True}
    assert run([swin(0.1)], meta=m)["verdict"] == "ai_edited"


def test_ai_edit_app_in_metadata_is_ai_edited():
    m = {**META, "ai_edit_tools": ["remini"], "editing_software_detected": ["remini"]}
    a = run([swin(0.1), cf("cf_frontier", 0.1, "real"), cf("cf_lowq", 0.1, "real")], meta=m)
    assert a["verdict"] == "ai_edited" and a["rules"] == ["R1e"]


def test_unavailable_second_family_falls_back_to_single_detector_rules():
    a = run([swin(0.85), {"key": "cf_frontier", "model": "x", "family": "community_forensics", "status": "unavailable"}])
    assert a["verdict"] == "inconclusive"  # a lone raw-score detector needs >= 0.90
    assert run([swin(0.93)])["verdict"] == "ai_likely"
