"""Builds a small labelled evaluation set from Wikimedia Commons (1024px thumbnails) for model selection.

Labels come from the Commons category: AI categories -> 'ai', photo categories -> 'real'.
Images already used as demo samples are excluded. Writes eval_images/manifest.json with provenance.
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "TruthLensHackathonEval/1.0 (educational model evaluation)"
OUT = Path(__file__).resolve().parents[1] / "eval_images"
CATS = {
    "ai": ["Images_generated_by_Stable_Diffusion", "Midjourney_images", "AI-generated_photorealistic_images",
           "Images_generated_by_DALL-E", "Images_generated_by_Adobe_Firefly"],
    "real": ["Quality_images_of_people", "Quality_images_of_landscapes", "Quality_images_of_animals",
             "Quality_images_of_streets", "Photographs_by_NASA"],
}
PER_CAT = 6
EXCLUDE = {"Hopetoun_falls", "Neil_Armstrong_pose", "colonized_comet", "AI_Artwork_of_Mountains"}


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                return data if binary else json.loads(data)
        except Exception as e:  # noqa: BLE001
            print("  retry", attempt, e)
            time.sleep(8 * (attempt + 1))
    return None


def main():
    OUT.mkdir(exist_ok=True)
    manifest = []
    for label, cats in CATS.items():
        for cat in cats:
            q = urllib.parse.urlencode({"action": "query", "generator": "categorymembers", "gcmtitle": f"Category:{cat}",
                                        "gcmtype": "file", "gcmlimit": 40, "prop": "imageinfo",
                                        "iiprop": "url|mime|size|extmetadata", "iiurlwidth": 1280, "format": "json"})
            res = get(f"https://commons.wikimedia.org/w/api.php?{q}")
            pages = list(((res or {}).get("query") or {}).get("pages", {}).values())
            n = 0
            for p in pages:
                ii = (p.get("imageinfo") or [{}])[0]
                if ii.get("mime") not in ("image/jpeg", "image/png") or any(x in ii.get("url", "") for x in EXCLUDE):
                    continue
                name = f"{label}_{cat[:18]}_{n}.jpg" if ii["mime"] == "image/jpeg" else f"{label}_{cat[:18]}_{n}.png"
                time.sleep(4)
                data = get(ii.get("thumburl") or ii["url"], binary=True)  # 1280px = Wikimedia standard thumb size
                if not data:
                    continue
                (OUT / name).write_bytes(data)
                meta = ii.get("extmetadata", {})
                manifest.append({"file": name, "label": label, "category": cat, "title": p["title"],
                                 "license": meta.get("LicenseShortName", {}).get("value"),
                                 "source": ii.get("descriptionurl")})
                n += 1
                print(label, cat, name)
                if n >= PER_CAT:
                    break
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print("total", len(manifest))


if __name__ == "__main__":
    main()
