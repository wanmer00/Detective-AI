"""Face overlay drawing must not crash on boxes that touch or cross the image border.

Found by the pipeline benchmark (scripts/benchmark_pipeline.py): on a 320-px copy of a portrait, YuNet returned a
box starting above the frame (y < 0) and the label rectangle had y1 < y0, which made the whole upload fail.
"""
import pytest
from PIL import Image

from app.services.face_analysis import faces as F


@pytest.mark.parametrize("box", [[10, -8, 60, 60], [10, 0, 60, 60], [-5, 3, 40, 40], [280, 150, 60, 60]])
def test_overlay_handles_boxes_at_the_border(monkeypatch, box):
    monkeypatch.setattr(F.face_detector, "backend", "test")
    monkeypatch.setattr(F.face_detector, "detect", lambda img: [{"box": list(box), "detection_confidence": 0.9}])
    result, overlay = F.analyze_faces(Image.new("RGB", (320, 179), (90, 90, 90)))
    assert result["face_count"] == 1 and overlay is not None and overlay.size == (320, 179)
