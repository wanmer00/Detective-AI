"""Forensic timeline: every timestamp embedded in the file, ordered, plus consistency checks.

Principles:
- Only timestamps actually present in the file are listed; nothing is inferred or invented.
- Missing timestamps are reported as "not present", never as evidence of manipulation.
- Every check returns what it found AND what it means, including innocent explanations.
"""
import re
from datetime import datetime, timedelta, timezone

from PIL import ExifTags, Image

from app.i18n import M, render
from app.services.forensics.metadata import extract_xmp

EXIF_DT = "%Y:%m:%d %H:%M:%S"
MAX_HISTORY = 200  # edit-history events reported (DoS guard)


def _parse_exif_dt(v, offset: str | None = None) -> datetime | None:
    if not v:
        return None
    s = str(v).strip().replace("\x00", "")
    if not s or s.startswith("0000"):
        return None
    try:
        dt = datetime.strptime(s[:19], EXIF_DT)
    except ValueError:
        return None
    if offset and re.fullmatch(r"[+-]\d{2}:\d{2}", offset.strip()):
        sign = 1 if offset.strip()[0] == "+" else -1
        hh, mm = map(int, offset.strip()[1:].split(":"))
        dt = dt.replace(tzinfo=timezone(sign * timedelta(hours=hh, minutes=mm)))
    return dt


def _parse_iso(v: str) -> datetime | None:
    s = v.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M%z", "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.replace("Z", "+0000").replace("+00:00", "+0000") if "%z" in fmt else s, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _iso(dt: datetime) -> str:
    return dt.isoformat(sep=" ")


def _cmp(a: datetime, b: datetime) -> float | None:
    """Seconds a-b. Naive vs aware: compared as wall-clock (timezone unknown)."""
    if (a.tzinfo is None) != (b.tzinfo is None):
        a, b = a.replace(tzinfo=None), b.replace(tzinfo=None)
    return (a - b).total_seconds()


def build_timeline(data: bytes, img: Image.Image, fmt: str, scan_time: datetime) -> dict:
    events: list[dict] = []
    raw: dict = {}

    # ---- EXIF ---------------------------------------------------------------
    try:
        exif = img.getexif()
        base = {ExifTags.TAGS.get(k, str(k)): v for k, v in exif.items()}
        sub = {ExifTags.TAGS.get(k, str(k)): v for k, v in exif.get_ifd(ExifTags.IFD.Exif).items()}
        gps = {ExifTags.GPSTAGS.get(k, str(k)): v for k, v in exif.get_ifd(ExifTags.IFD.GPSInfo).items()}
    except Exception:  # noqa: BLE001
        base, sub, gps = {}, {}, {}
    for k in ("OffsetTime", "OffsetTimeOriginal", "OffsetTimeDigitized", "SubsecTimeOriginal"):
        if sub.get(k):
            raw[k] = str(sub[k]).strip("\x00 ")
    software = str(base.get("Software") or "").strip("\x00 ") or None

    SOURCE_KEY = {"EXIF": "exif", "EXIF GPS": "exifGps", "XMP": "xmp", "XMP history": "xmpHistory",
                  "PNG text chunk": "png", "Detective AI": "app"}

    def add(dt, source, field, meaning, kind):
        """meaning: i18n message."""
        if dt:
            events.append({"time": _iso(dt), "_dt": dt, "source": source, "source_key": SOURCE_KEY[source], "field": field,
                           "meaning": render(meaning), "meaning_msg": meaning, "kind": kind,
                           "timezone": "stated" if dt.tzinfo else "not stated (local time)",
                           "tz": "stated" if dt.tzinfo else "local"})

    E = "dyn.tl.ev."
    t_orig = _parse_exif_dt(sub.get("DateTimeOriginal"), raw.get("OffsetTimeOriginal"))
    t_dig = _parse_exif_dt(sub.get("DateTimeDigitized"), raw.get("OffsetTimeDigitized"))
    t_mod = _parse_exif_dt(base.get("DateTime"), raw.get("OffsetTime"))
    add(t_orig, "EXIF", "DateTimeOriginal", M(E + "dateTimeOriginal"), "capture")
    add(t_dig, "EXIF", "DateTimeDigitized", M(E + "dateTimeDigitized"), "capture")
    add(t_mod, "EXIF", "DateTime (ModifyDate)", M(E + "modify", sw=M(E + "modifySw", sw=software) if software else ""), "modify")

    t_gps = None
    if gps.get("GPSDateStamp") and gps.get("GPSTimeStamp"):
        try:
            h, m, s = (float(x) for x in gps["GPSTimeStamp"])
            d = datetime.strptime(str(gps["GPSDateStamp"]).strip("\x00 "), "%Y:%m:%d")
            t_gps = d.replace(hour=int(h), minute=int(m), second=int(s), tzinfo=timezone.utc)
            add(t_gps, "EXIF GPS", "GPSDateStamp + GPSTimeStamp", M(E + "gps"), "capture")
        except Exception:  # noqa: BLE001
            pass

    # ---- XMP ---------------------------------------------------------------
    xmp, _ = extract_xmp(data)  # linear-time, size-capped
    xmp_times = {}
    for tag, meaning, kind in (("xmp:CreateDate", M(E + "xmpCreate"), "create"),
                               ("xmp:ModifyDate", M(E + "xmpModify"), "modify"),
                               ("xmp:MetadataDate", M(E + "xmpMetadata"), "modify"),
                               ("photoshop:DateCreated", M(E + "psCreated"), "create"),
                               ("exif:DateTimeOriginal", M(E + "xmpExifOriginal"), "capture")):
        mm = re.search(rf'{tag}="([^"]{{1,64}})"|<{tag}>([^<]{{1,64}})</{tag}>', xmp)
        if mm:
            dt = _parse_iso(mm.group(1) or mm.group(2))
            xmp_times[tag] = dt
            add(dt, "XMP", tag, meaning, kind)
    tool = re.search(r'xmp:CreatorTool="([^"]{1,300})"|<xmp:CreatorTool>([^<]{1,300})<', xmp)
    creator_tool = (tool.group(1) or tool.group(2)) if tool else None

    # Edit history: linear scan. Each event's fields follow its stEvt:action, so look only in a bounded
    # window up to the next action (no backtracking over attacker-controlled XMP).
    history = []
    actions = list(re.finditer(r'stEvt:action(?:="([^"<>]{1,100})"|>([^<]{1,100})<)', xmp))[:MAX_HISTORY]
    for i, act in enumerate(actions):
        stop = actions[i + 1].start() if i + 1 < len(actions) else len(xmp)
        block = xmp[act.start():min(stop, act.start() + 2000)]
        when = re.search(r'stEvt:when(?:="([^"]{1,64})"|>([^<]{1,64})<)', block)
        agent = re.search(r'stEvt:softwareAgent(?:="([^"]{1,300})"|>([^<]{1,300})<)', block)
        a = act.group(1) or act.group(2)
        w = _parse_iso(when.group(1) or when.group(2)) if when else None
        g = (agent.group(1) or agent.group(2)) if agent else None
        history.append({"action": a, "when": _iso(w) if w else None, "software": g})
        add(w, "XMP history", f"stEvt:action={a}",
            M(E + "history", action=a, agent=M(E + "historyAgent", agent=g) if g else ""), "edit")

    # ---- PNG ---------------------------------------------------------------
    if fmt == "PNG":
        for k, v in (img.info or {}).items():
            if isinstance(v, str) and k.lower() in ("creation time", "date:create", "date:modify", "time"):
                dt = _parse_iso(v) or None
                add(dt, "PNG text chunk", k, M(E + "png"), "create")

    # ---- Scan --------------------------------------------------------------
    events.append({"time": _iso(scan_time), "_dt": scan_time, "source": "Detective AI", "source_key": "app",
                   "field": render(M(E + "scanField")), "field_msg": M(E + "scanField"),
                   "meaning": render(M(E + "scan")), "meaning_msg": M(E + "scan"), "kind": "scan",
                   "timezone": "UTC", "tz": "utc"})

    # ---- Checks ------------------------------------------------------------
    checks = []
    C = "dyn.tl.chk."

    def check(cid, status, title_params=None, **detail_params):
        title = M(f"{C}{cid}.title", **(title_params or {}))
        detail = M(f"{C}{cid}.detail", **detail_params)
        meaning = M(f"{C}{cid}.meaning")
        checks.append({"id": cid, "status": status, "title": render(title), "title_msg": title,
                       "detail": render(detail), "detail_msg": detail, "meaning": render(meaning), "meaning_msg": meaning})

    embedded = [e for e in events if e["kind"] != "scan"]
    if not embedded:
        check("no_timestamps", "info")
    if t_orig and t_mod:
        d = _cmp(t_mod, t_orig)
        if d is not None and d < -60:
            check("modify_before_capture", "warning", modify=_iso(t_mod), hours=f"{abs(d)/3600:.1f}", orig=_iso(t_orig))
        elif d is not None and d > 120:
            check("modified_after_capture", "notice", days=f"{d/86400:.1f}",
                  sw=M(C + "modified_after_capture.detailSw", sw=software) if software else "")
        else:
            check("capture_modify_consistent", "ok")
    if t_orig and t_dig and t_orig.tzinfo == t_dig.tzinfo and abs(_cmp(t_orig, t_dig) or 0) > 60:
        check("orig_digitized_mismatch", "notice", a=_iso(t_orig), b=_iso(t_dig))
    future = [e for e in embedded if (_cmp(e["_dt"], scan_time) or 0) > 86400]
    if future:
        check("future_dates", "warning", list=", ".join(f"{e['field']} = {e['time']}" for e in future))
    ancient = [e for e in embedded if e["_dt"].year < 1990]
    if ancient:
        check("implausible_dates", "notice", list=", ".join(f"{e['field']} = {e['time']}" for e in ancient))
    xo = xmp_times.get("xmp:CreateDate") or xmp_times.get("exif:DateTimeOriginal")
    if t_orig and xo:
        d = abs(_cmp(xo, t_orig) or 0)
        if d > 60 and abs(d - round(d / 3600) * 3600) > 60:
            check("exif_xmp_mismatch", "warning", exif=_iso(t_orig), xmp=_iso(xo), hours=f"{d/3600:.1f}")
    if t_gps and t_orig:
        d = abs(_cmp(t_gps, t_orig.replace(tzinfo=t_orig.tzinfo or None)) or 0)
        if d > 15 * 3600:
            check("gps_time_mismatch", "warning", hours=f"{d/3600:.1f}")
        else:
            check("gps_time_consistent", "ok", hours=f"{d/3600:.1f}")
    if (software or creator_tool) and not history and t_mod and t_orig and abs(_cmp(t_mod, t_orig) or 0) <= 120:
        check("software_no_time_change", "notice", sw=software or creator_tool)
    if history:
        acts = sorted({h["action"] for h in history})
        agents = sorted({h["software"] for h in history if h["software"]})
        check("edit_history", "notice", {"n": len(history)}, actions=", ".join(acts),
              agents=M(C + "edit_history.detailAgents", agents=", ".join(agents)) if agents else "")
    if not any(c["status"] in ("warning",) for c in checks) and embedded:
        check("no_inconsistency", "ok", n=len(embedded))

    events.sort(key=lambda e: (e["_dt"].replace(tzinfo=None), e["kind"] == "scan"))
    for e in events:
        e.pop("_dt")
    return {
        "events": events,
        "edit_history": history,
        "software": software,
        "creator_tool": creator_tool,
        "timezone_offsets": raw,
        "checks": checks,
        "embedded_count": len(embedded),
    }
