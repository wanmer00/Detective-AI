"""Scan testing/ folders and update testing/manifest.csv.

- Creates the manifest with the 50 planned placeholder cases if it does not exist.
- A new image file in a category folder fills a planned slot of that category:
    * a file whose name contains a slot ID (e.g. DA-C05-002_myedit.jpg) goes to that slot,
    * otherwise the first still-empty slot of the category, in ID order.
  If all slots are used, a new row is appended (ground truth taken from the category, or TBD).
- Records path, SHA-256, size, format and dimensions. Never renames, moves or modifies image files.
- Already registered files are re-hashed: a changed file is marked `changed` (originals must not be overwritten);
  a vanished file is marked `missing`.
- Manual columns (tools, prompts, links, notes) are never overwritten.

Usage (from backend/):  .venv\\Scripts\\python scripts\\scan_test_dataset.py
"""
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dataset_lib import (CATEGORIES, FIELDS, IMAGE_EXT, LABELS, MANIFEST, ROOT, planned_rows, read_manifest,  # noqa: E402
                         root_of, sha256, write_manifest)

ID_RE = re.compile(r"DA-[A-Z]\d{2}-\d{3}")


def describe(p: Path) -> dict:
    info = {"file_size": p.stat().st_size, "sha256": sha256(p), "format": "", "width": "", "height": ""}
    try:
        with Image.open(p) as im:
            info.update(format=im.format or "", width=im.width, height=im.height)
    except Exception as e:  # noqa: BLE001
        info["format"] = f"UNREADABLE ({type(e).__name__})"
    return info


def main():
    for folder, _, _ in CATEGORIES.values():
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    (ROOT / "results").mkdir(parents=True, exist_ok=True)

    rows = read_manifest()
    if not rows:
        rows = planned_rows()
        print(f"Created manifest with {len(rows)} planned test cases.")
    by_id = {r["image_id"]: r for r in rows}
    by_path = {r["file_path"]: r for r in rows if r["file_path"]}
    notes = []

    # 1. Re-check registered files.
    for r in rows:
        if not r["file_path"]:
            continue
        p = ROOT / r["file_path"]
        if not p.is_file():
            if r["slot_status"] != "missing":
                notes.append(f"MISSING  {r['image_id']}: {r['file_path']} no longer exists")
            r["slot_status"] = "missing"
        elif sha256(p) != r["sha256"]:
            if r["slot_status"] != "changed":
                notes.append(f"CHANGED  {r['image_id']}: {r['file_path']} differs from the registered file "
                             "(originals must not be overwritten; restore it or clear the row's file columns to re-register)")
            r["slot_status"] = "changed"
        elif r["slot_status"] in ("missing", "changed"):
            r["slot_status"] = "present"

    # 2. Register new files.
    for cat, (folder, default, desc) in CATEGORIES.items():
        for p in sorted((ROOT / folder).iterdir()):
            if not p.is_file() or p.name.startswith(".") or p.name.endswith((".md", ".txt", ".csv")):
                continue
            rel = p.relative_to(ROOT).as_posix()
            if rel in by_path:
                continue
            if p.suffix.lower() not in IMAGE_EXT:
                notes.append(f"SKIPPED  {rel}: unsupported type (use JPG, PNG or WEBP)")
                continue
            m = ID_RE.search(p.name)
            slot = by_id.get(m.group(0)) if m else None
            if slot and (slot["test_category"] != cat or slot["file_path"]):
                slot = None
            if not slot:
                slot = next((r for r in rows if r["test_category"] == cat and not r["file_path"]), None)
            if not slot:
                n = 1 + max((int(r["image_id"][-3:]) for r in rows if r["test_category"] == cat), default=0)
                slot = {k: "" for k in FIELDS}
                slot |= {"image_id": f"DA-{cat}-{n:03d}", "test_category": cat, "planned_case": "(extra, not in plan)",
                        "ground_truth": "TBD" if default in ("inherit", "TBD") else default, "original_image_id": "",
                        "transformation": "none (original)" if folder.startswith("originals") else desc,
                        "include_in_metrics": "yes"}
                rows.append(slot)
                by_id[slot["image_id"]] = slot
            slot.update(describe(p), file_path=rel, slot_status="present", added_date=date.today().isoformat())
            if not slot.get("provenance_notes"):
                slot["provenance_notes"] = f"added file name: {p.name}"
            by_path[rel] = slot
            notes.append(f"ADDED    {slot['image_id']} <- {rel}")

    # 3. Derived fields: source groups, inherited labels, unreadable files.
    for r in rows:
        r["source_group_id"] = root_of(r["image_id"], by_id)
        o = by_id.get(r["original_image_id"])
        if CATEGORIES[r["test_category"]][1] == "inherit" and o and o["ground_truth"] in LABELS:
            r["ground_truth"] = o["ground_truth"]
        if r["original_image_id"] and r["original_image_id"] not in by_id:
            notes.append(f"WARNING  {r['image_id']}: original_image_id {r['original_image_id']} does not exist")
        if r["format"].startswith("UNREADABLE"):
            notes.append(f"WARNING  {r['image_id']}: file cannot be decoded")
        if r["slot_status"] == "present" and r["ground_truth"] not in LABELS:
            notes.append(f"TODO     {r['image_id']}: set ground_truth (one of {', '.join(LABELS)}) in manifest.csv")

    write_manifest(rows)

    print("\n".join(notes) or "No changes in folders.")
    present = Counter(r["test_category"] for r in rows if r["slot_status"] == "present")
    total = Counter(r["test_category"] for r in rows)
    print("\nCategory  present/planned")
    for cat in CATEGORIES:
        if total[cat]:
            print(f"  {cat}     {present[cat]}/{total[cat]}   {CATEGORIES[cat][2]}")
    print(f"\n{sum(present.values())} of {len(rows)} test cases have an image. Manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
