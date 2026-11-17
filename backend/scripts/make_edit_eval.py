"""Builds a small labelled EDITED-image test set from the REAL images of eval_images/eval_set.jsonl.

Edit types (each the kind of thing seen in memes, thumbnails and fake 'evidence' images):
  splice   - a region from a different photo pasted in (different camera noise / compression)
  graphic  - a smooth computer-graphics element (gradient shape) composited in
  text     - large overlay text with outline, thumbnail style
Every output is re-saved as JPEG q=85 so the whole image shares one final compression, as after
any messenger or social-network upload. Output: eval_images/edits/ + edit_set.jsonl
"""
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

EV = Path(__file__).resolve().parents[1] / "eval_images"
OUT = EV / "edits"
OUT.mkdir(exist_ok=True)
rng = random.Random(7)
rows = [json.loads(x) for x in (EV / "eval_set.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
reals = [EV / r["file"] for r in rows if r["label"] == "REAL"]


def load(p, max_side=1280):
    im = Image.open(p).convert("RGB")
    im.thumbnail((max_side, max_side))
    return im


def splice(base, donor):
    W, H = base.size
    w, h = int(W * rng.uniform(.25, .4)), int(H * rng.uniform(.25, .4))
    dw, dh = donor.size
    x, y = rng.randint(0, dw - min(w, dw)), rng.randint(0, dh - min(h, dh))
    patch = donor.crop((x, y, x + min(w, dw), y + min(h, dh))).resize((w, h))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, w, h), fill=255)
    base.paste(patch, (rng.randint(0, W - w), rng.randint(0, H - h)), mask.filter(ImageFilter.GaussianBlur(6)))
    return base


def graphic(base, _):
    W, H = base.size
    w, h = int(W * .35), int(H * .35)
    yy, xx = np.mgrid[0:h, 0:w]
    g = np.stack([xx / w * 255, yy / h * 200 + 30, np.full_like(xx, 220.0)], -1).astype(np.uint8)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, w, h), fill=255)
    base.paste(Image.fromarray(g), (int(W * .55), int(H * .1)), mask.filter(ImageFilter.GaussianBlur(3)))
    return base


def text(base, _):
    W, H = base.size
    d = ImageDraw.Draw(base)
    try:
        font = ImageFont.load_default(size=max(24, W // 9))
    except TypeError:
        font = ImageFont.load_default()
    d.text((int(W * .05), int(H * .05)), "BREAKING", font=font, fill=(255, 255, 255), stroke_width=max(2, W // 200),
           stroke_fill=(0, 0, 0))
    return base


def save(im, name):
    im.save(OUT / name, "JPEG", quality=85)


out_rows = []
for i, p in enumerate(reals):
    base = load(p)
    save(base.copy(), f"real_{i:02d}.jpg")
    out_rows.append({"file": f"edits/real_{i:02d}.jpg", "label": "UNEDITED", "explanation": f"{p.name} re-saved q85"})
    kind = ["splice", "graphic", "text"][i % 3]
    donor = load(reals[(i + 3) % len(reals)])
    edited = {"splice": splice, "graphic": graphic, "text": text}[kind](base.copy(), donor)
    save(edited, f"edit_{kind}_{i:02d}.jpg")
    out_rows.append({"file": f"edits/edit_{kind}_{i:02d}.jpg", "label": "EDITED", "explanation": f"{kind} applied to {p.name}"})
(EV / "edit_set.jsonl").write_text("\n".join(json.dumps(r) for r in out_rows) + "\n", encoding="utf-8")
print(len(out_rows), "images ->", EV / "edit_set.jsonl")
