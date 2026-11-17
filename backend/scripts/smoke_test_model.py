"""Minimal inference test for the selected detector. Usage (from backend/):
    .venv\\Scripts\\python scripts\\smoke_test_model.py ..\\sample_images\\ai_stable_diffusion_comet.jpg
"""
import sys
import time

import torch
from huggingface_hub import snapshot_download
from PIL import Image
from transformers import AutoImageProcessor, SiglipForImageClassification

REPO = "Ateeqq/ai-vs-human-image-detector"
path = snapshot_download(REPO, local_dir="models_cache/siglip_ai_vs_human",
                         allow_patterns=["config.json", "preprocessor_config.json", "model.safetensors"])
dev = "cuda" if torch.cuda.is_available() else "cpu"
proc = AutoImageProcessor.from_pretrained(path)
model = SiglipForImageClassification.from_pretrained(path).eval().to(dev)
print(f"device={dev} params={sum(p.numel() for p in model.parameters())/1e6:.1f}M labels={model.config.id2label}")
for f in sys.argv[1:]:
    img = Image.open(f).convert("RGB")
    t = time.perf_counter()
    with torch.inference_mode():
        probs = torch.softmax(model(**proc(images=img, return_tensors="pt").to(dev)).logits, -1)[0].cpu()
    print(f"{f}: " + ", ".join(f"{model.config.id2label[i]}={p:.4f}" for i, p in enumerate(probs))
          + f"  ({(time.perf_counter()-t)*1000:.0f} ms)")
if dev == "cuda":
    print(f"peak VRAM: {torch.cuda.max_memory_allocated()/1e6:.0f} MB")
