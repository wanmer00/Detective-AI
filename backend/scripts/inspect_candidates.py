"""Download and print small metadata files (config, calibrator, reports) of candidate detectors."""
import json
import os
import sys

from huggingface_hub import hf_hub_download

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
FILES = {
    "Thermostatic/community-forensics-low-quality-detector-2026-08": ["config.json", "calibrator.json", "reports/final_report.md"],
    "Thermostatic/community-forensics-frontier-detector-2026-08": ["config.json", "calibrator.json", "README.md"],
    "buildborderless/CommunityForensics-DeepfakeDet-ViT": ["config.json", "README.md"],
}
for repo, files in FILES.items():
    for f in files:
        try:
            p = hf_hub_download(repo, f, cache_dir=sys.argv[1])
        except Exception as e:  # noqa: BLE001
            print(f"##### {repo}/{f}: ERR {e}")
            continue
        txt = open(p, encoding="utf-8").read()
        print(f"##### {repo}/{f} ({len(txt)} chars)")
        if f.endswith(".json"):
            print(json.dumps(json.loads(txt), indent=None)[:1800])
        else:
            print(" ".join(txt.split())[:3200])
