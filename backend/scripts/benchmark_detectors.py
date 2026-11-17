"""Benchmarks candidate AI-image detectors on eval_images/ (labelled via manifest.json).

Each image is also re-encoded as a phone-like JPEG (q=80, 1280px) because real-world uploads are
recompressed; a detector that only works on pristine files is useless for the demo.
Usage: .venv\\Scripts\\python scripts\\benchmark_detectors.py [extra_real.jpg ...]
"""
import io
import json
import sys
from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from PIL import Image, ImageOps
from transformers import AutoImageProcessor, AutoModelForImageClassification

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = {
    "Ateeqq/ai-vs-human-image-detector": ["ai"],
    "haywoodsloan/ai-image-detector-deploy": ["artificial"],
    "Organika/sdxl-detector": ["artificial"],
    "prithivMLmods/AI-vs-Deepfake-vs-Real-Siglip2": ["ai", "deepfake"],
    "Smogy/SMOGY-Ai-images-detector": ["artificial"],
}
PATTERNS = ["config.json", "preprocessor_config.json", "model.safetensors"]


def recompress(img):
    im = img.copy()
    im.thumbnail((1280, 1280))
    b = io.BytesIO()
    im.save(b, "JPEG", quality=80)
    return Image.open(io.BytesIO(b.getvalue())).convert("RGB")


def main():
    lines = (ROOT / "eval_images" / "eval_set.jsonl").read_text(encoding="utf-8").splitlines()
    items = [json.loads(x) for x in lines if x.strip()]
    data = [(ROOT / "eval_images" / i["file"], "ai" if i["label"] == "AI_GENERATED" else "real") for i in items]
    data += [(Path(p), "real") for p in sys.argv[1:]]
    imgs = [(ImageOps.exif_transpose(Image.open(p)).convert("RGB"), lab, p.name) for p, lab in data]
    print(f"{len(imgs)} images: {sum(l == 'ai' for _, l, _ in imgs)} ai / {sum(l == 'real' for _, l, _ in imgs)} real")
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    results, per_image = {}, {}
    for repo, pos in CANDIDATES.items():
        path = snapshot_download(repo, local_dir=ROOT / "models_cache" / ("bench_" + repo.replace("/", "__")),
                                 allow_patterns=PATTERNS)
        proc = AutoImageProcessor.from_pretrained(path)
        model = AutoModelForImageClassification.from_pretrained(path).eval().to(dev)
        idx = [i for i, l in model.config.id2label.items() if l.lower() in pos]
        rows = []
        for variant in ("original", "recompressed"):
            correct = tp = fp = n_ai = n_real = 0
            for img, lab, name in imgs:
                x = img if variant == "original" else recompress(img)
                with torch.inference_mode():
                    p = torch.softmax(model(**proc(images=x, return_tensors="pt").to(dev)).logits.float(), -1)[0]
                s = float(p[idx].sum())
                pred = "ai" if s >= 0.5 else "real"
                correct += pred == lab
                if lab == "ai":
                    n_ai += 1
                    tp += pred == "ai"
                else:
                    n_real += 1
                    fp += pred == "ai"
                if variant == "original":
                    per_image.setdefault(name, {"label": lab})[repo] = round(s, 3)
            rows.append(f"{variant}: acc={correct/len(imgs):.2f} AI-recall={tp/max(n_ai,1):.2f} "
                        f"false-AI-on-real={fp/max(n_real,1):.2f}")
        results[repo] = rows
        print(repo, "|", " || ".join(rows), flush=True)
        del model
        torch.cuda.empty_cache()
    out = ROOT / "eval_images" / "benchmark_results.json"
    out.write_text(json.dumps({"summary": results, "per_image": per_image}, indent=1), encoding="utf-8")
    print("saved", out)


if __name__ == "__main__":
    main()
