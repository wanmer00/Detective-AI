"""Digital image forensic investigation report (ReportLab), localised (en / ru / az).

Static labels come from pdf.* keys and dynamic findings from the i18n message objects stored in the report,
falling back to the stored English text for scans made before localisation existed.
"""
import io
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (Image as RLImage, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

from app.core.config import settings
from app.i18n import APP_NAME, M, norm_lang, render

# Unicode font with Cyrillic and Azerbaijani Latin (ə, ı, ğ, ş …). Falls back to Helvetica (Latin-1 only).
FONT, FONT_B = "Helvetica", "Helvetica-Bold"
for reg, bold in (("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
                  ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")):
    if Path(reg).exists() and Path(bold).exists():
        try:
            pdfmetrics.registerFont(TTFont("TLSans", reg))
            pdfmetrics.registerFont(TTFont("TLSans-Bold", bold))
            FONT, FONT_B = "TLSans", "TLSans-Bold"
            break
        except Exception:  # noqa: BLE001
            pass

NAVY = colors.HexColor("#0B1220")
BLUE = colors.HexColor("#1F6FE0")
GREY = colors.HexColor("#5B6475")
LINE = colors.HexColor("#D5DAE3")
SOFT = colors.HexColor("#F2F5FA")
VERDICT_COLOR = {"ai_likely": "#C93C42", "ai_edited": "#A1349A", "authentic_likely": "#2A8C5C", "not_ai": "#0B76B0",
                 "manipulated_possible": "#C98A12", "inconclusive": "#6B7280"}
STATUS_COLOR = {"points_ai": "#C93C42", "points_camera": "#2A8C5C", "points_edit": "#C98A12", "neutral": "#5B6475",
                "unreliable": "#D9731A", "unavailable": "#9AA1AD"}
CHECK_COLOR = {"ok": "#2A8C5C", "info": "#0B76B0", "notice": "#C98A12", "warning": "#C93C42"}


def _safe(s) -> str:
    s = str(s)
    if FONT == "Helvetica":
        s = s.replace("→", "->").replace("≥", ">=").replace("≤", "<=").replace("×", "x").replace("≈", "~").replace("·", "-")
    return escape(s)


S = {
    "title": ParagraphStyle("t", fontName=FONT_B, fontSize=19, leading=23, textColor=NAVY),
    "sub": ParagraphStyle("s", fontName=FONT, fontSize=9, leading=12, textColor=GREY),
    "h1": ParagraphStyle("h1", fontName=FONT_B, fontSize=12.5, leading=16, textColor=NAVY, spaceBefore=12, spaceAfter=5),
    "h2": ParagraphStyle("h2", fontName=FONT_B, fontSize=9.5, leading=12, textColor=BLUE, spaceBefore=6, spaceAfter=3),
    "b": ParagraphStyle("b", fontName=FONT, fontSize=8.6, leading=11.4, textColor=colors.HexColor("#1D2433")),
    "small": ParagraphStyle("sm", fontName=FONT, fontSize=7.4, leading=9.6, textColor=GREY),
    "mono": ParagraphStyle("mo", fontName="Courier", fontSize=7.6, leading=9.6, textColor=colors.HexColor("#1D2433")),
    "cellb": ParagraphStyle("cb", fontName=FONT_B, fontSize=8, leading=10, textColor=NAVY),
    "cell": ParagraphStyle("c", fontName=FONT, fontSize=7.8, leading=10, textColor=colors.HexColor("#1D2433")),
}


def P(t, st="b"):
    return Paragraph(_safe(t), S[st])


def tag(text, hexcol):
    return Paragraph(f'<font color="{hexcol}"><b>{_safe(text)}</b></font>', S["cell"])


def grid(rows, widths, header=True, zebra=True):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
    if zebra:
        st += [("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, SOFT])]
    t.setStyle(TableStyle(st))
    return t


def kv(rows, w1=44):
    return grid([[P(k, "cellb"), v if not isinstance(v, str) else P(v, "cell")] for k, v in rows],
                [w1 * mm, (178 - w1) * mm], header=False)


def hdr(cells):
    return [Paragraph(f'<font color="white"><b>{_safe(c)}</b></font>', S["cell"]) for c in cells]


class NumberedCanvas(rl_canvas.Canvas):
    """Adds the localised header, 'Page x of y', case ID and evidence hash to every page."""

    def __init__(self, *a, labels=None, **k):
        super().__init__(*a, **k)
        self._saved, self.labels = [], labels or {}

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        n = len(self._saved)
        lb = self.labels
        for state in self._saved:
            self.__dict__.update(state)
            w, h = A4
            self.setStrokeColor(LINE)
            self.line(16 * mm, h - 11 * mm, w - 16 * mm, h - 11 * mm)
            self.line(16 * mm, 11 * mm, w - 16 * mm, 11 * mm)
            self.setFont(FONT_B, 7.5)
            self.setFillColor(NAVY)
            self.drawString(16 * mm, h - 9 * mm, lb["header"])
            self.setFont(FONT, 7.5)
            self.setFillColor(GREY)
            self.drawRightString(w - 16 * mm, h - 9 * mm, lb["right"])
            self.setFont("Courier", 6.5)
            self.drawString(16 * mm, 7.5 * mm, lb["hash"])
            self.setFont(FONT, 7.5)
            self.drawRightString(w - 16 * mm, 7.5 * mm, lb["page"](self._pageNumber, n))
            super().showPage()
        super().save()


def build_pdf(r: dict, lang: str = "en") -> bytes:
    lang = norm_lang(lang)

    def T(key, **params):
        return render(M(key, **params), lang)

    def R(msg, fallback=""):
        """Render a stored i18n message, or fall back to the stored English text (older scans)."""
        return render(msg, lang) if msg else (fallback or "")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=15 * mm,
                            bottomMargin=15 * mm, title=T("pdf.title") + f" — {r['scan_id']}", author=APP_NAME)
    a, f, m = r["assessment"], r["file"], r["metadata"]
    tl = r.get("timeline") or {}
    signals = r.get("signals") or []
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    el = []

    # ---- Cover / case summary -------------------------------------------------
    el += [P(T("pdf.title"), "title"), P(T("pdf.subtitle", id=r["scan_id"], date=generated), "sub"), Spacer(1, 8)]
    vc = colors.HexColor(VERDICT_COLOR.get(a["verdict"], "#6B7280"))
    conf = a.get("detection_confidence")
    if conf:
        ind = T("confidence." + conf["level"])
        if a["ai_likelihood"] is not None:
            ind += f" ({a['ai_likelihood']:.2f})"
    elif a["ai_likelihood"] is not None:
        ind = f"{a['ai_likelihood']:.2f} ({T('band.' + (a.get('ai_likelihood_band') or 'uncertain').replace(' ', '_'))})"
    elif a.get("detector_agreement") == "unstable":
        ind = T("pdf.noReliableSmall" if a.get("unstable_reason") == "low_resolution" else "pdf.noReliable")
    else:
        ind = T("pdf.notDetermined")
    counts = {k: sum(s["status"] == k for s in signals) for k in STATUS_COLOR}
    box = Table([[Paragraph(f'<font color="white">{_safe(T("pdf.assessment"))}</font>',
                            ParagraphStyle("vk", fontName=FONT_B, fontSize=7.5, leading=10))],
                 [Paragraph(f'<font color="white">{_safe(T("verdict." + a["verdict"]))}</font>',
                            ParagraphStyle("vt", fontName=FONT_B, fontSize=16, leading=20))],
                 [Paragraph('<font color="white">' + _safe(T("pdf.summary", strength=T("evidenceStrength." + a["evidence_strength"]),
                                                              indicator=ind, ai=counts["points_ai"], cam=counts["points_camera"],
                                                              edit=counts["points_edit"], unrel=counts["unreliable"])) + "</font>", S["b"])]],
                colWidths=[178 * mm])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), vc), ("LEFTPADDING", (0, 0), (-1, -1), 9),
                             ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    el += [box, Spacer(1, 8)]

    el.append(P(T("pdf.evidenceItem"), "h2"))
    el.append(kv([
        (T("pdf.caseId"), r["scan_id"]), (T("pdf.filename"), r["filename"]),
        (T("pdf.received"), r["created_at"]), (T("pdf.format"), f"{f['format']} ({f['mime']}), {f['mode']}"),
        (T("pdf.dimensions"), f"{f['width']} × {f['height']} px"), (T("pdf.fileSize"), T("pdf.bytes", n=f"{f['size_bytes']:,}")),
        ("SHA-256", Paragraph(_safe(f["sha256"]), S["mono"])),
    ]))
    el += [Spacer(1, 4), P(T("pdf.integrity"), "small")]

    # ---- 1. Assessment ---------------------------------------------------------
    el.append(P(T("pdf.s1"), "h1"))
    el.append(P(T("pdf.how"), "h2"))
    rule_msgs = a.get("rules_msgs") or []
    el += [P("• " + R(rm, fb)) for rm, fb in zip(rule_msgs or [None] * len(a["rules_fired"]), a["rules_fired"])]
    fams = a.get("detector_families") or []
    if fams:
        el.append(P(T("pdf.detectors"), "h2"))
        dets = {d.get("key"): d for d in r["detectors"]}
        rows = [hdr([T("pdf.colDetector"), T("pdf.colDecision"), T("pdf.colScore"), T("pdf.colRule")])]
        dec_col = {"ai": "#C93C42", "real": "#2A8C5C", "uncertain": "#5B6475", "unreliable": "#D9731A"}
        for fam in fams:
            vote = T("results.familySplit") if fam["split"] else T("results.familyVote", vote=T("decision." + fam["vote"]))
            for mb in fam["members"]:
                d = dets.get(mb["key"], {})
                rows.append([Paragraph(f"<b>{_safe(mb['name'])}</b><br/><font color='#5B6475'>{_safe(T('results.familyLabel', family=fam['name']))}"
                                       f" — {_safe(vote)}</font>", S["cell"]),
                             tag(T("decision." + mb["decision"]).upper(), dec_col.get(mb["decision"], "#5B6475")),
                             P(f"{mb['score']:.3f} — {T('scoreKind.' + mb['score_kind'])}", "cell"),
                             P(" · ".join(x for x in (d.get("threshold"), d.get("input")) if x) or "—", "cell")])
        el.append(grid(rows, [44 * mm, 22 * mm, 46 * mm, 66 * mm]))
        el.append(P(T("pdf.confNote"), "small"))
    q = a.get("image_quality") or {}
    if q.get("low_quality"):
        el.append(P(T("results.qualityTitle"), "h2"))
        if "small" in q["reasons"]:
            el.append(P(T("results.qualitySmall", side=q["long_side"], min=q["min_long_side"])))
        if "compressed" in q["reasons"]:
            el.append(P(T("results.qualityCompressed", q=q["jpeg_quality"], max=q["max_jpeg_quality"])))
        el.append(P(T("results.qualityText"), "small"))
    for title, items in ((T("pdf.evFor"), a["evidence_for_ai"]), (T("pdf.evAgainst"), a["evidence_against_ai"]),
                         (T("pdf.evEdit"), a["manipulation_indicators"])):
        el.append(P(title, "h2"))
        el += [P(f"[{T('strength.' + e['strength'])}] [{T('source.' + e['source'])}] {R(e.get('msg'), e['text'])}") for e in items] \
            or [P(T("pdf.noneFound"), "small")]
    el.append(P(T("pdf.next"), "h2"))
    rec_msgs = a.get("recommendations_msgs") or [None] * len(a["recommendations"])
    el += [P("• " + R(rm, fb)) for rm, fb in zip(rec_msgs, a["recommendations"])]

    # ---- 2. Signals ------------------------------------------------------------
    if signals:
        el.append(P(T("pdf.s2"), "h1"))
        el.append(P(T("pdf.s2note"), "small"))
        rows = [hdr([T("pdf.colSignal"), T("pdf.colValue"), T("pdf.colStatus"), T("pdf.colFinding")])]
        for s in signals:
            group = T("signalGroup." + s["group_key"]) if s.get("group_key") else s["group"]
            value = R(s.get("value_msg"), s.get("value") or "—")
            rows.append([Paragraph(f"<b>{_safe(R(s.get('name_msg'), s['name']))}</b><br/><font color='#5B6475'>{_safe(group)}</font>", S["cell"]),
                         Paragraph(_safe(value), S["cell"]), tag(T("signalStatus." + s["status"]).upper(), STATUS_COLOR[s["status"]]),
                         Paragraph(f"{_safe(R(s.get('finding_msg'), s['finding']))}<br/><font color='#5B6475'>"
                                   f"{_safe(R(s.get('meaning_msg'), s['meaning']))}</font>", S["cell"])])
        el.append(grid(rows, [40 * mm, 28 * mm, 26 * mm, 84 * mm]))

    # ---- 3. Timeline -----------------------------------------------------------
    el.append(P(T("pdf.s3"), "h1"))
    if tl:
        rows = [hdr([T("pdf.colTime"), T("pdf.colSource"), T("pdf.colField"), T("pdf.colMeaning")])]
        for e in tl.get("events", []):
            src = T("tlSource." + e["source_key"]) if e.get("source_key") else e["source"]
            tz = T("tz." + e["tz"]) if e.get("tz") else e.get("timezone", "")
            rows.append([Paragraph(_safe(e["time"]), S["mono"]), P(src, "cell"), P(R(e.get("field_msg"), e["field"]), "cell"),
                         Paragraph(_safe(R(e.get("meaning_msg"), e["meaning"])) +
                                   (f" <font color='#5B6475'>{_safe(T('pdf.tzNote', tz=tz))}</font>" if e["kind"] != "scan" else ""), S["cell"])])
        el.append(grid(rows, [38 * mm, 24 * mm, 36 * mm, 80 * mm]))
        el.append(P(T("pdf.checks"), "h2"))
        rows = [hdr([T("pdf.colResult"), T("pdf.colCheck"), T("pdf.colDetail")])]
        for c in tl.get("checks", []):
            rows.append([tag(T("checkStatus." + c["status"]), CHECK_COLOR[c["status"]]), P(R(c.get("title_msg"), c["title"]), "cellb"),
                         Paragraph(f"{_safe(R(c.get('detail_msg'), c['detail']))}<br/><font color='#5B6475'>"
                                   f"{_safe(R(c.get('meaning_msg'), c['meaning']))}</font>", S["cell"])])
        el.append(grid(rows, [26 * mm, 46 * mm, 106 * mm]))
        if tl.get("edit_history"):
            el.append(P(T("pdf.history"), "h2"))
            rows = [hdr([T("pdf.colWhen"), T("pdf.colAction"), T("pdf.colSoftware")])] + \
                [[P(h["when"] or "—", "cell"), P(h["action"], "cell"), P(h["software"] or "—", "cell")] for h in tl["edit_history"]]
            el.append(grid(rows, [45 * mm, 35 * mm, 98 * mm]))
    else:
        el.append(P(T("pdf.noTimeline"), "small"))

    # ---- 4. Visual evidence ----------------------------------------------------
    scan_dir = settings.scans_dir / r["scan_id"]
    labels = {"original": T("pdf.exA"), "saliency": T("pdf.exB"), "faces": T("pdf.exC"), "ela": T("pdf.exD")}
    imgs = [(k, scan_dir / f"{k}.jpg") for k in labels if (scan_dir / f"{k}.jpg").exists()]
    if imgs:
        el += [PageBreak(), P(T("pdf.s4"), "h1")]
        cells = []
        for k, p in imgs:
            im = RLImage(str(p))
            ratio = im.imageHeight / im.imageWidth
            im.drawWidth, im.drawHeight = 84 * mm, 84 * mm * ratio
            if im.drawHeight > 95 * mm:
                im.drawHeight, im.drawWidth = 95 * mm, 95 * mm / ratio
            cells.append([im, P(labels[k], "small")])
        rows = []
        for i in range(0, len(cells), 2):
            pair = cells[i:i + 2] + ([[P(""), P("")]] if len(cells[i:i + 2]) == 1 else [])
            rows += [[pair[0][0], pair[1][0]], [pair[0][1], pair[1][1]]]
        t = Table(rows, colWidths=[89 * mm, 89 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        el.append(t)
        el.append(P(T("pdf.exNote"), "small"))
        fa = r["faces"]
        if fa.get("faces"):
            el.append(P(T("pdf.faces"), "h2"))
            rows = [hdr(["#", T("pdf.colBox"), T("pdf.colDet"), T("pdf.colManip"), T("pdf.colFlagged")])]
            for fc in fa["faces"]:
                score = fc.get("manipulation_score")
                rows.append([P(fc["id"], "cell"), P(fc["box"], "cell"), P(fc.get("detection_confidence") or "—", "cell"),
                             P(score if score is not None else (T(fc["note_key"]) if fc.get("note_key") else "—"), "cell"),
                             P(T("pdf.yes") if fc.get("flagged") else T("pdf.no"), "cell")])
            el.append(grid(rows, [10 * mm, 50 * mm, 32 * mm, 44 * mm, 42 * mm]))

    # ---- 5. Technical metadata -------------------------------------------------
    el.append(P(T("pdf.s5"), "h1"))
    markers = m.get("ai_generation_marker_msgs")
    el.append(kv([
        (T("pdf.camera"), " ".join(filter(None, (m["camera"] or {}).values())) or T("pdf.notPresent")),
        (T("pdf.swTag"), m["software"] or "—"), (T("pdf.creatorTool"), tl.get("creator_tool") or "—"),
        (T("pdf.editSw"), ", ".join(m["editing_software_detected"]) or T("pdf.noneDetected")),
        (T("pdf.aiMarkers"), (R(markers) if markers else "; ".join(m["ai_generation_markers"])) or T("pdf.noneDetected")),
        (T("pdf.c2pa"), f"{T('pdf.c2paPresent') if m['c2pa']['present'] else T('pdf.c2paNotFound')} ({m['c2pa']['reader']})"),
        (T("pdf.jpegQ"), f"~{r['signal']['jpeg']['estimated_quality']}" if r["signal"].get("jpeg") else "—"),
        (T("pdf.ela"), T("pdf.elaValue", mean=r["signal"]["ela"]["mean_error"], p99=r["signal"]["ela"]["p99_error"],
                         nu=r["signal"]["ela"]["block_nonuniformity"])),
    ]))
    if m.get("exif"):
        el.append(P(T("pdf.exifFields"), "h2"))
        el.append(grid([hdr([T("pdf.colTag"), T("pdf.colValue")])] + [[P(k, "cell"), P(v, "cell")] for k, v in m["exif"].items()],
                       [45 * mm, 133 * mm]))

    # ---- 6. Methodology --------------------------------------------------------
    el.append(KeepTogether([P(T("pdf.s6"), "h1"),
                            grid([hdr([T("pdf.colComponent"), T("pdf.colModel"), T("pdf.colLicense"), T("pdf.colStatus")])] +
                                 [[P(T("pdf.compAi"), "cell"), P(d["model"], "cell"), P(d["license"], "cell"),
                                   P(f"{d['status']}{' · ' + d['device'] if d.get('device') else ''}", "cell")]
                                  for d in r["detectors"]] +
                                 [[P(T("pdf.compFace"), "cell"), P(r["faces"].get("detector") or "—", "cell"),
                                   P("Apache-2.0", "cell"), P(r["faces"].get("status", "—"), "cell")],
                                  [P(T("pdf.compFaceManip"), "cell"), P(r["faces"].get("manipulation_classifier") or "—", "cell"),
                                   P("Apache-2.0", "cell"), P(r["faces"].get("manipulation_classifier_status") or "—", "cell")]],
                                 [34 * mm, 74 * mm, 26 * mm, 44 * mm]),
                            Spacer(1, 4), P(R(a.get("method_msg"), a["method"]), "small"), P(T("pdf.multiview"), "small")]))

    # ---- 7. Limitations --------------------------------------------------------
    el.append(P(T("pdf.s7"), "h1"))
    lim_msgs = a.get("limitations_msgs") or [None] * len(a["limitations"])
    el += [P("• " + R(lm, fb)) for lm, fb in zip(lim_msgs, a["limitations"])]
    el += [Spacer(1, 10), P(T("pdf.declaration"), "small")]

    page_lbl = lambda n, total: T("pdf.page", n=n, total=total)  # noqa: E731
    labels = {"header": T("pdf.header"), "right": T("pdf.headerRight", id=r["scan_id"]),
              "hash": T("pdf.hashFooter", sha=f["sha256"]), "page": page_lbl}
    doc.build(el, canvasmaker=lambda *ar, **kw: NumberedCanvas(*ar, labels=labels, **kw))
    return buf.getvalue()
