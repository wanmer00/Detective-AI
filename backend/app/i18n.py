"""Server-side i18n. Single source of truth: frontend/src/locales/{en,ru,az}.json (shared with the UI).

Dynamic analysis text is emitted as message objects {"key": ..., "params": {...}} so the UI can render it in
the user's current language at any time; an English rendering is stored alongside for API clients and tests.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parents[2] / "frontend" / "src" / "locales"
LANGS = ("en", "ru", "az")
APP_NAME = "Detective AI"
_PH = re.compile(r"\{(\w+)\}")


def _flat(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        out.update(_flat(v, key) if isinstance(v, dict) else {key: v})
    return out


@lru_cache(maxsize=None)
def catalog(lang: str) -> dict:
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        return {}
    return _flat(json.loads(path.read_text(encoding="utf-8")))


def norm_lang(lang: str | None) -> str:
    lang = (lang or "en").lower()[:2]
    return lang if lang in LANGS else "en"


def M(key: str, **params) -> dict:
    """A translatable message."""
    return {"key": key, "params": params}


def render(msg, lang: str = "en") -> str:
    """Render a message object (or plain string) in `lang`, falling back to English, then to the key."""
    if msg is None:
        return ""
    if isinstance(msg, str):
        return msg
    if isinstance(msg, list):
        return "; ".join(render(m, lang) for m in msg)
    if not isinstance(msg, dict) or "key" not in msg:
        return str(msg)
    lang = norm_lang(lang)
    template = catalog(lang).get(msg["key"]) or catalog("en").get(msg["key"]) or msg["key"]
    params = {"app": APP_NAME, **(msg.get("params") or {})}
    return _PH.sub(lambda m: render(params[m.group(1)], lang) if m.group(1) in params else m.group(0), template)


def t(key: str, lang: str = "en", **params) -> str:
    return render(M(key, **params), lang)


def item(strength: str, source: str, msg: dict) -> dict:
    """Evidence item: English text kept for API clients, message for localisation."""
    return {"strength": strength, "source": source, "text": render(msg), "msg": msg}
