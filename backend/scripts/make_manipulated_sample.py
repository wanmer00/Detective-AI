"""Creates the documented copy-move forgery demo sample from the Hopetoun Falls photo.

The pasted region is resized/feathered slightly so it is plausible; the result is saved at a
different JPEG quality than the original, which is the classic scenario ELA is designed to expose.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2] / "sample_images"
src = Image.open(ROOT / "real_landscape_hopetoun_falls.jpg")
exif = src.info.get("exif", b"")
img = src.convert("RGB")
w, h = img.size
# Copy a block of fern/foliage from the lower-left and paste it over the upper-right area.
box = (int(w * 0.05), int(h * 0.62), int(w * 0.30), int(h * 0.92))
patch = img.crop(box)
mask = Image.new("L", patch.size, 0)
ImageDraw.Draw(mask).ellipse((0, 0, *patch.size), fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(25))
img.paste(patch, (int(w * 0.66), int(h * 0.10)), mask)
img.save(ROOT / "manipulated_copymove_hopetoun.jpg", "JPEG", quality=75, exif=exif)
print("written", ROOT / "manipulated_copymove_hopetoun.jpg")
