from app.services.aggregation.aggregate import aggregate

META = {"ai_generation_markers": [], "c2pa": {"present": False}, "camera": None, "capture_settings_present": False,
        "exif_present": False, "editing_software_detected": [], "edit_history_in_xmp": False}
SIG = {"format": "PNG", "width": 512, "height": 512, "jpeg": None, "ela": {"block_nonuniformity": 0.5}}
FACES = {"faces": [], "face_count": 0}


def det(score, role="primary", status="ok"):
    return {"model": f"m-{role}", "role": role, "status": status, "positive_score": score}


def test_agreeing_high_is_ai():
    a = aggregate([det(0.97), det(0.91, "secondary")], META, SIG, FACES)
    assert a["verdict"] == "ai_likely" and a["evidence_strength"] == "strong"


def test_disagreement_is_inconclusive():
    a = aggregate([det(0.97), det(0.05, "secondary")], META, SIG, FACES)
    assert a["verdict"] == "inconclusive" and a["detectors_disagree"]


def test_low_scores_without_provenance_is_not_ai_only():
    a = aggregate([det(0.03), det(0.1, "secondary")], META, SIG, FACES)
    assert a["verdict"] == "not_ai"


def test_low_scores_with_camera_exif_is_authentic():
    m = {**META, "exif_present": True, "camera": {"make": "Apple", "model": "iPhone 15"}, "capture_settings_present": True}
    assert aggregate([det(0.03)], m, SIG, FACES)["verdict"] == "authentic_likely"


def test_metadata_marker_wins():
    m = {**META, "ai_generation_markers": ["Diffusion prompt parameters embedded"]}
    assert aggregate([det(0.4)], m, SIG, FACES)["verdict"] == "ai_likely"


def test_no_detectors_not_fabricated():
    a = aggregate([det(None, status="unavailable")], META, SIG, FACES)
    assert a["ai_likelihood"] is None and a["verdict"] == "inconclusive"


def test_single_detector_flags_limited_evidence():
    a = aggregate([det(0.95)], META, SIG, FACES)
    assert any("limited evidence" in x for x in a["limitations"])


def test_camera_exif_resolves_disagreement():
    m = {**META, "exif_present": True, "camera": {"make": "Apple", "model": "iPhone 15"}, "capture_settings_present": True}
    assert aggregate([det(0.99), det(0.01, "secondary")], m, SIG, FACES)["verdict"] == "authentic_likely"


def test_camera_exif_does_not_override_unanimous_ai():
    # Camera EXIF never turns unanimous AI detections into "authentic"; since the AI-edited category exists the
    # combination is reported as an AI-edited photo (or an AI image with copied EXIF), rule R2e.
    m = {**META, "exif_present": True, "camera": {"make": "Apple", "model": "iPhone 15"}, "capture_settings_present": True}
    a = aggregate([det(0.99), det(0.97, "secondary")], m, SIG, FACES)
    assert a["verdict"] == "ai_edited" and a["rules"] == ["R2e"]


def test_unstable_single_detector_reports_no_score():
    d = {**det(0.99), "stable": False, "stability": 0.57, "view_scores": {"full": 0.99, "top": 0.04}}
    a = aggregate([d], META, SIG, FACES)
    assert a["ai_likelihood"] is None and a["detector_agreement"] == "unstable" and a["verdict"] != "ai_likely"


def test_small_unstable_image_explains_low_resolution():
    d = {**det(0.14), "stable": False, "stability": 0.57, "view_scores": {"full": 0.58, "right": 0.98}}
    a = aggregate([d], META, {**SIG, "width": 281, "height": 367}, FACES)
    assert a["unstable_reason"] == "low_resolution" and a["low_resolution"]
    assert any("281×367" in x for x in a["limitations"])


def test_missing_exif_is_not_evidence():
    a = aggregate([det(0.5)], META, SIG, FACES)
    assert not any("EXIF" in e["text"] for e in a["evidence_for_ai"])
