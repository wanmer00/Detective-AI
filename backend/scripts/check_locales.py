"""Checks that en/ru/az locale files have identical keys and identical {placeholders} per key.

Usage (from backend/):  .venv\\Scripts\\python scripts\\check_locales.py
"""
import json
import re
import sys
from pathlib import Path

LOC = Path(__file__).resolve().parents[2] / "frontend" / "src" / "locales"


def flat(d, p=""):
    out = {}
    for k, v in d.items():
        key = f"{p}.{k}" if p else k
        out.update(flat(v, key) if isinstance(v, dict) else {key: v})
    return out


cats = {lang: flat(json.loads((LOC / f"{lang}.json").read_text(encoding="utf-8"))) for lang in ("en", "ru", "az")}
ph = lambda s: sorted(set(re.findall(r"\{(\w+)\}", s)))  # noqa: E731
problems = 0
for lang in ("ru", "az"):
    missing = sorted(set(cats["en"]) - set(cats[lang]))
    extra = sorted(set(cats[lang]) - set(cats["en"]))
    for k in missing:
        print(f"[{lang}] MISSING {k}")
    for k in extra:
        print(f"[{lang}] EXTRA   {k}")
    for k in set(cats["en"]) & set(cats[lang]):
        if ph(cats["en"][k]) != ph(cats[lang][k]):
            print(f"[{lang}] PLACEHOLDERS differ in {k}: en={ph(cats['en'][k])} {lang}={ph(cats[lang][k])}")
            problems += 1
    problems += len(missing) + len(extra)
print(f"{len(cats['en'])} keys per language; {problems} problem(s)")
sys.exit(1 if problems else 0)
