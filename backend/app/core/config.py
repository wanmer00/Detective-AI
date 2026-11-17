"""Application configuration loaded from environment variables (.env supported)."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_prefix="TRUTHLENS_", extra="ignore")

    data_dir: Path = BACKEND_DIR / "data"
    models_dir: Path = BACKEND_DIR / "models_cache"
    database_url: str = ""  # defaults to sqlite in data_dir
    max_upload_mb: int = 15
    max_pixels: int = 40_000_000  # decompression-bomb guard
    min_dimension: int = 32
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    device: str = "auto"  # auto | cpu | cuda
    enable_saliency: bool = True
    offline: bool = True  # never contact the HF hub at runtime; run scripts/download_models.py first
    # Which AI detectors to load (keys from AI_DETECTORS). Used by benchmarks to reproduce the old single-model setup.
    detectors: str = "swinv2_ai_detector,cf_frontier,cf_lowq"
    # Quality gate: below these, the system will not claim "no AI" (detector recall drops; see benchmark report).
    low_quality_long_side: int = 512
    low_quality_jpeg: int = 75

    @property
    def db_url(self) -> str:
        return self.database_url or f"sqlite:///{(self.data_dir / 'truthlens.db').as_posix()}"

    @property
    def scans_dir(self) -> Path:
        return self.data_dir / "scans"

    @property
    def tmp_dir(self) -> Path:
        return self.data_dir / "tmp"


settings = Settings()
for d in (settings.data_dir, settings.scans_dir, settings.tmp_dir, settings.models_dir):
    d.mkdir(parents=True, exist_ok=True)

# Pretrained models used by Detective AI. All weights are downloaded once into models_dir.
# Ateeqq/ai-vs-human-image-detector (SigLIP) was removed after benchmarking on eval_images/eval_set.jsonl:
# 5/20 wrong (3 real photos called AI, incl. a fresh smartphone photo) vs 3/20 for SwinV2 alone.
# The two Community Forensics models were added after the false-negative investigation of 17-Nov-2026
# (testing/results/detector_benchmark_20261117_163217): recall 18/19 vs 11/19 for SwinV2 on the same images.
# They share a lineage (lowq is fine-tuned from frontier), so the aggregator counts them as ONE family vote.
AI_DETECTORS = [
    {
        "key": "swinv2_ai_detector",
        "name": "SwinV2",
        "repo": "haywoodsloan/ai-image-detector-deploy",
        "arch": "SwinV2 (image classification)",
        "license": "Apache-2.0",
        "ai_labels": ["artificial", "ai", "fake"],
        "role": "primary",
        "family": "swinv2",
        "kind": "hf",
    },
    {
        "key": "cf_frontier",
        "name": "CF frontier",
        "repo": "Thermostatic/community-forensics-frontier-detector-2026-08",
        "arch": "ViT-S/16-384 (Community Forensics, timm)",
        "license": "MIT",
        "role": "secondary",
        "family": "community_forensics",
        "kind": "timm_cf",
        "revision": "16db135220b318d811b207db576d90368980b595",
        "sha256": "2f445aecc310caee9b55d3ae0aeebc404a32d72e5836e30523ce0a9a1720cd47",
    },
    {
        "key": "cf_lowq",
        "name": "CF low-quality",
        "repo": "Thermostatic/community-forensics-low-quality-detector-2026-08",
        "arch": "ViT-S/16-384 (Community Forensics, low-quality fine-tune, timm)",
        "license": "MIT",
        "role": "secondary",
        "family": "community_forensics",
        "kind": "timm_cf",
        "revision": "6fca3e7f4365363ee5c0fdb1a17d73917d54413d",
        "sha256": "c09206330c97a759ff4d38cc9a05617928525ecdc0a8ebc1552ffc361bae1791",
    },
]
FACE_MANIPULATION_MODEL = {
    "key": "vit_deepfake_faces",
    "repo": "prithivMLmods/Deep-Fake-Detector-v2-Model",
    "arch": "ViT-B/16 (ViTForImageClassification)",
    "license": "Apache-2.0",
    "fake_labels": ["deepfake"],
}
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
YUNET_FILE = "face_detection_yunet_2023mar.onnx"
