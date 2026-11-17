"""Upload validation: size limits, magic-byte checks, safe decoding, decompression-bomb guard."""
import hashlib
import io
import secrets
import warnings

from PIL import Image, ImageOps

from .config import settings

ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAGIC = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")
# ISO-BMFF brands: HEIC/HEIF (iPhone default) and AVIF.
HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1", b"heim", b"heis"}
AVIF_BRANDS = {b"avif", b"avis"}

try:  # HEIC/HEIF decoding (iPhone photos) via pillow-heif
    import pillow_heif

    pillow_heif.register_heif_opener()
    ALLOWED_FORMATS["HEIF"] = "image/heic"
    ALLOWED_EXT |= {".heic", ".heif"}
except ImportError:
    pass
try:  # AVIF decoding is built into recent Pillow
    from PIL import features

    if features.check("avif"):
        ALLOWED_FORMATS["AVIF"] = "image/avif"
        ALLOWED_EXT |= {".avif"}
except Exception:  # noqa: BLE001
    pass

Image.MAX_IMAGE_PIXELS = settings.max_pixels
warnings.simplefilter("error", Image.DecompressionBombWarning)


class UploadError(ValueError):
    """User-facing validation error. `code` + `params` map to errors.<code> in the locale files;
    str(e) is the English message (safe to return to clients)."""

    def __init__(self, code: str, **params):
        from app.i18n import t

        self.code, self.params = code, params
        super().__init__(t(f"errors.{code}", **params))


def sniff(data: bytes) -> bool:
    if data.startswith(MAGIC) or (data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
        return True
    if data[4:8] == b"ftyp":
        brands = {data[i:i + 4] for i in range(8, min(len(data), 64), 4)}
        return bool(brands & ((HEIF_BRANDS if "HEIF" in ALLOWED_FORMATS else set()) |
                              (AVIF_BRANDS if "AVIF" in ALLOWED_FORMATS else set())))
    return False


def validate_image_bytes(data: bytes, filename: str) -> tuple[Image.Image, dict]:
    if not data:
        raise UploadError("empty")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise UploadError("tooLarge", mb=settings.max_upload_mb)
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_txt = ", ".join(sorted(e.lstrip(".").upper() for e in ALLOWED_EXT))
    if ext not in ALLOWED_EXT:
        raise UploadError("badExtension", allowed=allowed_txt)
    if not sniff(data):
        raise UploadError("notImage", allowed=allowed_txt)
    try:
        probe = Image.open(io.BytesIO(data))
        fmt = probe.format
        if fmt not in ALLOWED_FORMATS:
            raise UploadError("formatNotAllowed")
        w, h = probe.size
        if w * h > settings.max_pixels:
            raise UploadError("tooManyPixels")
        if min(w, h) < settings.min_dimension:
            raise UploadError("tooSmall", min=settings.min_dimension)
        probe.verify()  # structural integrity check
        img = Image.open(io.BytesIO(data))
        img.load()
    except UploadError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise UploadError("bomb")
    except Exception:
        raise UploadError("decode")
    info = {
        "format": fmt,
        "mime": ALLOWED_FORMATS[fmt],
        "width": w,
        "height": h,
        "mode": img.mode,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "animated": bool(getattr(img, "is_animated", False)),
    }
    return img, info


def to_rgb(img: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(img) if img.format in ("JPEG", "HEIF", "AVIF", "WEBP") else img
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")


def new_scan_id() -> str:
    return "TL-" + secrets.token_hex(6).upper()


def safe_filename(name: str) -> str:
    keep = "".join(c for c in name if c.isalnum() or c in "._- ")[:120].strip()
    return keep or "image"
