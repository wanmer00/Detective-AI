"""One-time model download. After this, Detective AI runs fully offline.

Usage (from backend/):  .venv\\Scripts\\python scripts\\download_models.py
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from huggingface_hub import snapshot_download  # noqa: E402

from app.core.config import AI_DETECTORS, FACE_MANIPULATION_MODEL, YUNET_FILE, YUNET_URL, settings  # noqa: E402

PATTERNS = ["config.json", "preprocessor_config.json", "model.safetensors", "pytorch_model.bin",
            "README.md", "tokenizer*", "special_tokens_map.json", "calibrator.json"]


def main() -> None:
    for spec in [*AI_DETECTORS, FACE_MANIPULATION_MODEL]:
        target = settings.models_dir / spec["key"]
        print(f"Downloading {spec['repo']} -> {target}")
        snapshot_download(spec["repo"], local_dir=target, allow_patterns=PATTERNS, revision=spec.get("revision"))
        if spec.get("sha256"):  # pinned weights: refuse anything other than the benchmarked file
            digest = hashlib.sha256((target / "model.safetensors").read_bytes()).hexdigest()
            if digest != spec["sha256"]:
                raise SystemExit(f"{spec['repo']}: weight hash {digest} != pinned {spec['sha256']}")
    yunet = settings.models_dir / YUNET_FILE
    if not yunet.exists():
        print(f"Downloading YuNet face detector -> {yunet}")
        urllib.request.urlretrieve(YUNET_URL, yunet)
    print("All models downloaded.")


if __name__ == "__main__":
    main()
