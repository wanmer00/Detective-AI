import { AlertTriangle, ArrowLeft, Camera, CheckCircle2, Clock, Cpu, Download, Eye, FileSearch, Fingerprint, Hash, Info, Loader2, PenTool, ScanFace, ShieldAlert, Sparkles, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { fmtBytes, ScoreBar, Strength, VERDICT_META, VerdictBadge } from "../components/ui";
import { errorText, useI18n } from "../i18n";
import type { Msg } from "../i18n";
import { api } from "../services/api";
import type { ConfidenceLevel, Decision, Evidence, Report, Signal, TimelineCheck, TimelineEvent } from "../types";

const VIS_KEYS = ["original", "saliency", "faces", "ela"] as const;
type VisKey = (typeof VIS_KEYS)[number];
const SECTIONS = ["assessment", "signals", "evidence", "metadata", "limitations"] as const;

const SIGNAL_STYLE: Record<Signal["status"], { cls: string; icon: typeof Sparkles }> = {
  points_ai: { cls: "bg-rose-500/10 text-rose-300 ring-rose-500/30", icon: Sparkles },
  points_camera: { cls: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30", icon: Camera },
  points_edit: { cls: "bg-amber-500/10 text-amber-300 ring-amber-500/30", icon: PenTool },
  neutral: { cls: "bg-white/5 text-slate-300 ring-white/10", icon: Info },
  unreliable: { cls: "bg-orange-500/10 text-orange-300 ring-orange-500/30", icon: AlertTriangle },
  unavailable: { cls: "bg-white/5 text-slate-500 ring-white/10", icon: XCircle },
};

const CHECK_STYLE: Record<TimelineCheck["status"], { cls: string; icon: typeof Info }> = {
  ok: { cls: "text-emerald-300", icon: CheckCircle2 },
  info: { cls: "text-sky-300", icon: Info },
  notice: { cls: "text-amber-300", icon: Info },
  warning: { cls: "text-rose-300", icon: AlertTriangle },
};

const CONF_COLOR: Record<ConfidenceLevel, string> = {
  high: "text-white", moderate: "text-slate-200", limited: "text-amber-300", conflict: "text-amber-300", none: "text-slate-400",
};
const DEC_STYLE: Record<Decision, string> = {
  ai: "bg-rose-500/10 text-rose-300", real: "bg-emerald-500/10 text-emerald-300",
  uncertain: "bg-white/5 text-slate-300", unreliable: "bg-orange-500/10 text-orange-300",
};

const KIND_STYLE: Record<TimelineEvent["kind"], string> = {
  capture: "bg-emerald-400", create: "bg-sky-400", modify: "bg-amber-400", edit: "bg-rose-400", scan: "bg-electric-400",
};

function Block({ id, num, title, icon, children, right }: { id: string; num: number; title: string; icon: ReactNode; children: ReactNode; right?: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-24 fade-up">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.06] pb-2">
        <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-electric-300">
          <span className="font-mono text-slate-500">{String(num).padStart(2, "0")}</span>{icon}{title}
        </h2>
        {right}
      </div>
      {children}
    </section>
  );
}

function Card({ title, icon, children }: { title?: string; icon?: ReactNode; children: ReactNode }) {
  return (
    <div className="card card-pad min-w-0">
      {title && <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-white">{icon}{title}</h3>}
      {children}
    </div>
  );
}

function EvidenceList({ items, empty }: { items: Evidence[]; empty: string }) {
  const { t, tm } = useI18n();
  if (!items.length) return <p className="text-sm text-slate-500">{empty}</p>;
  return <ul className="space-y-2">{items.map((e, i) => (
    <li key={i} className="flex items-start gap-2 text-sm text-slate-300"><Strength s={e.strength} />
      <span className="min-w-0 break-words"><span className="text-slate-500">[{t(`source.${e.source}`)}]</span> {tm(e.msg, e.text)}</span></li>
  ))}</ul>;
}

function KV({ rows }: { rows: [string, ReactNode][] }) {
  return <dl className="divide-y divide-white/5 text-sm">{rows.map(([k, v]) => (
    <div key={k} className="grid grid-cols-[minmax(110px,40%)_1fr] gap-3 py-2 sm:grid-cols-[170px_1fr]"><dt className="text-slate-500">{k}</dt><dd className="min-w-0 break-words text-slate-200">{v}</dd></div>
  ))}</dl>;
}

/** Zip localisable messages with their stored English fallbacks (older scans have no messages). */
const zipMsgs = (msgs: Msg[] | undefined, texts: string[]) => texts.map((txt, i) => ({ msg: msgs?.[i], txt }));

export default function Results() {
  const { t, tm, tk, lang, fmtDate } = useI18n();
  const { id = "" } = useParams();
  const [r, setR] = useState<Report | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const [vis, setVis] = useState<VisKey>("original");
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => { setR(null); setErr(null); api.scan(id).then(setR).catch(setErr); }, [id]);

  if (err != null) return <div className="card card-pad text-sm text-rose-300">{errorText(t, err)} <Link to="/history" className="ml-2 text-electric-400">{t("common.backToHistory")}</Link></div>;
  if (!r) return <div className="flex items-center gap-2 py-20 text-slate-400"><Loader2 className="animate-spin" size={18} /> {t("results.loading")}</div>;
  const a = r.assessment;
  const vm = VERDICT_META[a.verdict] ?? VERDICT_META.inconclusive;
  const visKeys = VIS_KEYS.filter((k) => r.visuals[k]);
  const m = r.metadata;
  const signals = r.signals ?? [];
  const groupOf = (s: Signal) => s.group_key ?? s.group;
  const groups = [...new Set(signals.map(groupOf))];
  const tl = r.timeline;
  const counts = signals.reduce<Record<string, number>>((acc, s) => ({ ...acc, [s.status]: (acc[s.status] ?? 0) + 1 }), {});
  const band = a.ai_likelihood_band ? t(`band.${a.ai_likelihood_band.replace(/ /g, "_")}`) : "";
  const markers = m.ai_generation_marker_msgs?.length ? tm(m.ai_generation_marker_msgs) : m.ai_generation_markers.join("; ");
  const conf = a.detection_confidence;
  const q = a.image_quality;
  const fams = a.detector_families ?? [];

  return (
    <div className="space-y-10">
      {/* Evidence header */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link to="/history" className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white"><ArrowLeft size={15} /> {t("results.history")}</Link>
          <div className="flex flex-wrap gap-2">
            <Link to="/scan" className="btn-ghost">{t("common.newScan")}</Link>
            <a href={api.pdfUrl(r.scan_id, lang, true)} target="_blank" rel="noreferrer" className="btn-ghost">{t("results.viewReport")}</a>
            <a href={api.pdfUrl(r.scan_id, lang)} className="btn-primary"><Download size={16} className="shrink-0" /> {t("results.download")}</a>
          </div>
        </div>
        <div className="card overflow-hidden">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-white/5 bg-ink-850/60 px-5 py-3 text-xs">
            <span className="label !text-electric-300">{t("results.caseLabel")}</span>
            <span className="font-mono text-white">{r.scan_id}</span>
            <span className="min-w-0 break-all text-slate-400">{t("results.evidenceItem")} <span className="text-slate-200">{r.filename}</span></span>
            <span className="text-slate-400">{t("results.receivedLabel")} <span className="text-slate-200">{fmtDate(r.created_at)}</span></span>
            {r.is_demo && <span className="chip bg-electric-500/10 text-electric-300">{t("common.demoSample")}</span>}
          </div>
          <div className="flex items-start gap-2 px-5 py-3 font-mono text-[11px] text-slate-400">
            <Hash size={13} className="mt-0.5 shrink-0 text-electric-400" /><span className="break-all">SHA-256 {r.file.sha256}</span>
          </div>
        </div>
        <nav className="flex flex-wrap gap-2">
          {SECTIONS.map((sid, i) => <a key={sid} href={`#${sid}`} className="chip border border-white/10 px-3 py-1 text-slate-400 hover:border-electric-500/50 hover:text-white"><span className="font-mono text-slate-600">{i + 1}</span> {t(`results.sections.${sid}`)}</a>)}
        </nav>
      </div>

      {/* 1. Assessment */}
      <Block id="assessment" num={1} title={t("results.sections.assessment")} icon={<ShieldAlert size={14} />}>
        <div className={`card card-pad ring-1 ${vm.ring}`}>
          <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
            <div className="min-w-0">
              <VerdictBadge verdict={a.verdict} full />
              <h1 className={`mt-3 text-2xl font-semibold sm:text-3xl ${vm.color}`}>{t(`verdict.${a.verdict}`)}</h1>
              <p className="mt-2 text-sm text-slate-400">
                {t("results.evidenceStrength")} <span className="text-white">{t(`evidenceStrength.${a.evidence_strength}`)}</span>
                {" · "}{t("results.signalsExamined", { n: signals.length })}{" · "}{t("results.detectorsProduced", { ok: a.detectors_available, total: a.detectors_total })}
              </p>
              <div className="mt-4 rounded-xl bg-ink-850 p-3">
                <div className="label mb-1.5">{t("results.howReached")}</div>
                {zipMsgs(a.rules_msgs, a.rules_fired).map(({ msg, txt }) => <div key={txt} className="font-mono text-xs text-slate-300">{tm(msg, txt)}</div>)}
              </div>
            </div>
            <div className="min-w-0 space-y-4">
              {conf && (
                <div>
                  <div className="label mb-2">{t("results.detectionConfidence")}</div>
                  <div className={`text-3xl font-semibold ${CONF_COLOR[conf.level]}`}>{t(`confidence.${conf.level}`)}</div>
                  <p className="mt-1 text-sm text-slate-300">{t(`results.confText.${conf.level}`, { n: conf.agreeing, total: conf.families, direction: conf.direction === "ai" ? t("results.dirAi") : t("results.dirReal") })}</p>
                  <p className="mt-1.5 text-[11px] text-slate-500">{t("results.confNote")} {t("results.calProb")}</p>
                </div>
              )}
              {q?.low_quality && (
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">
                  <div className="mb-1 flex items-center gap-1.5 font-semibold text-amber-200"><AlertTriangle size={13} className="shrink-0" /> {t("results.qualityTitle")}</div>
                  {q.reasons.includes("small") && <div>{t("results.qualitySmall", { side: q.long_side, min: q.min_long_side })}</div>}
                  {q.reasons.includes("compressed") && <div>{t("results.qualityCompressed", { q: q.jpeg_quality ?? "—", max: q.max_jpeg_quality })}</div>}
                  <div className="mt-1 text-amber-200/80">{t("results.qualityText")}</div>
                </div>
              )}
              {(!conf || a.ai_likelihood != null) && <div>
                <div className="label mb-2">{t("results.indicator")}</div>
                {a.ai_likelihood != null ? (<>
                  <div className="flex items-baseline gap-2"><span className="text-4xl font-semibold tabular-nums text-white">{a.ai_likelihood.toFixed(2)}</span><span className="text-sm text-slate-400">{band}</span></div>
                  <div className="mt-2"><ScoreBar value={a.ai_likelihood} /></div>
                  <p className="mt-1.5 text-[11px] text-slate-500">{t("results.rawNote")}</p>
                </>) : (
                  <div><div className="text-2xl font-semibold text-amber-300">{a.detector_agreement === "unstable" ? t("results.noReliable") : t("results.notDetermined")}</div>
                    <p className="mt-1 text-xs text-slate-400">{a.detector_agreement === "unstable" ? t("results.unstableText") : t("results.noConsistent")}</p>
                    {a.unstable_reason === "low_resolution" && (
                      <p className="mt-2 rounded-lg bg-amber-500/10 px-3 py-2 text-xs text-amber-200">{t("results.lowResCause", { w: r.file.width, h: r.file.height })}</p>
                    )}</div>
                )}
              </div>}
              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="rounded-xl bg-rose-500/5 p-2"><div className="text-lg font-semibold text-rose-300">{counts.points_ai ?? 0}</div><div className="text-slate-500">{t("results.countAi")}</div></div>
                <div className="rounded-xl bg-emerald-500/5 p-2"><div className="text-lg font-semibold text-emerald-300">{counts.points_camera ?? 0}</div><div className="text-slate-500">{t("results.countCam")}</div></div>
                <div className="rounded-xl bg-amber-500/5 p-2"><div className="text-lg font-semibold text-amber-300">{counts.points_edit ?? 0}</div><div className="text-slate-500">{t("results.countEdit")}</div></div>
              </div>
            </div>
          </div>
        </div>
        {fams.length > 0 && <div className="mt-4"><Card title={t("results.detectorsTitle")} icon={<Cpu size={15} className="shrink-0 text-electric-400" />}>
          <div className="space-y-3">{fams.map((f) => (
            <div key={f.family} className={`rounded-xl bg-ink-850 p-3 ring-1 ${f.split ? "ring-amber-500/30" : "ring-white/5"}`}>
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs">
                <span className="font-semibold text-white">{t("results.familyLabel", { family: f.name })}</span>
                {f.split ? <span className="chip bg-amber-500/10 text-amber-300">{t("results.familySplit")}</span>
                  : <span className={`chip ${DEC_STYLE[f.vote]}`}>{t("results.familyVote", { vote: t(`decision.${f.vote}`) })}</span>}
              </div>
              {f.members.length > 1 && <p className="mb-2 text-[11px] text-slate-500">{t("results.familyRelated", { n: f.members.length })}</p>}
              <div className="divide-y divide-white/5">{f.members.map((mb) => { const d = r.detectors.find((x) => x.key === mb.key); return (
                <div key={mb.key} className="grid items-start gap-1 py-2 text-xs sm:grid-cols-[1.2fr_auto_1fr] sm:gap-3">
                  <div className="min-w-0"><div className="text-slate-200">{mb.name}</div><div className="break-all font-mono text-[10px] text-slate-500">{mb.model}</div></div>
                  <span className={`chip justify-self-start ${DEC_STYLE[mb.decision]}`}>{t(`decision.${mb.decision}`)}</span>
                  <div className="min-w-0 text-slate-400"><span className="font-mono text-slate-200">{mb.score.toFixed(3)}</span> · {t(`scoreKind.${mb.score_kind}`)}
                    {(d?.threshold || d?.input) && <div className="break-words font-mono text-[10px] text-slate-500">{[d?.threshold, d?.input].filter(Boolean).join(" · ")}</div>}</div>
                </div>
              ); })}</div>
            </div>
          ))}</div>
        </Card></div>}
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <Card title={t("results.evFor")} icon={<Sparkles size={15} className="shrink-0 text-rose-300" />}><EvidenceList items={a.evidence_for_ai} empty={t("results.noneFound")} /></Card>
          <Card title={t("results.evAgainst")} icon={<Camera size={15} className="shrink-0 text-emerald-300" />}><EvidenceList items={a.evidence_against_ai} empty={t("results.noneFound")} /></Card>
          <Card title={t("results.evEdit")} icon={<PenTool size={15} className="shrink-0 text-amber-300" />}><EvidenceList items={a.manipulation_indicators} empty={t("results.noneFound")} /></Card>
        </div>
        <div className="mt-4"><Card title={t("results.nextSteps")}>
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-300">{zipMsgs(a.recommendations_msgs, a.recommendations).map(({ msg, txt }) => <li key={txt}>{tm(msg, txt)}</li>)}</ul>
        </Card></div>
      </Block>

      {/* 2. Signals */}
      <Block id="signals" num={2} title={t("results.sections.signals")} icon={<Cpu size={14} />} right={<span className="text-xs text-slate-500">{t("results.signalsHint")}</span>}>
        {signals.length === 0 ? <Card><p className="text-sm text-slate-500">{t("results.noSignals")}</p></Card> : (
          <div className="space-y-4">{groups.map((g) => (
            <div key={g} className="card overflow-hidden">
              <div className="border-b border-white/5 bg-ink-850/60 px-5 py-2 text-xs font-medium uppercase tracking-wider text-slate-400">{tk(`signalGroup.${g}`, g)}</div>
              <div className="divide-y divide-white/5">{signals.filter((s) => groupOf(s) === g).map((s) => {
                const st = SIGNAL_STYLE[s.status]; const I = st.icon; const isOpen = open === s.id;
                const value = s.value_msg ? tm(s.value_msg, s.value) : s.value;
                return (
                  <button key={s.id} onClick={() => setOpen(isOpen ? null : s.id)} className="block w-full px-5 py-3 text-left transition hover:bg-white/[0.02]">
                    <div className="grid items-center gap-2 sm:grid-cols-[1.3fr_1fr_auto]">
                      <div className="min-w-0"><div className="text-sm text-white">{tm(s.name_msg, s.name)}</div><div className="text-xs text-slate-400">{tm(s.finding_msg, s.finding)}</div></div>
                      <div className="min-w-0 break-words font-mono text-xs text-slate-300 sm:text-right">{value ?? "—"}</div>
                      <span className={`chip ring-1 ${st.cls} justify-self-start whitespace-nowrap sm:justify-self-end`}><I size={11} /> {t(`signalStatus.${s.status}`)}</span>
                    </div>
                    {isOpen && <p className="mt-2 rounded-lg bg-ink-850 p-3 text-xs text-slate-300"><span className="font-semibold text-electric-300">{t("results.whatMeans")} </span>{tm(s.meaning_msg, s.meaning)}</p>}
                  </button>
                );
              })}</div>
            </div>
          ))}</div>
        )}
        {r.detectors.filter((d) => d.view_scores).map((d) => (
          <div key={d.key} className="card card-pad mt-4">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-xs"><span className="min-w-0 break-all font-mono text-slate-300">{t("results.perView", { model: d.model })}</span>
              <span className={d.stable ? "text-emerald-300" : "text-amber-300"}>{d.stable ? t("results.stable") : t("results.unstable")} · {t("results.viewsAgree", { pct: Math.round((d.stability ?? 0) * 100) })}</span></div>
            <div className="grid grid-cols-4 gap-1 sm:grid-cols-7">{Object.entries(d.view_scores ?? {}).map(([k, v]) => (
              <div key={k} className={`rounded-md px-1.5 py-1 text-center font-mono text-[10px] ${v >= 0.5 ? "bg-rose-500/10 text-rose-200" : "bg-emerald-500/10 text-emerald-200"}`}>{tk(`views.${k}`, k)}<br />{v.toFixed(2)}</div>
            ))}</div>
          </div>
        ))}
      </Block>

      {/* 3. Evidence */}
      <Block id="evidence" num={3} title={t("results.sections.evidence")} icon={<FileSearch size={14} />}>
        <div className="grid gap-4 lg:grid-cols-[1.1fr_1fr]">
          <Card title={t("results.timeline")} icon={<Clock size={15} className="text-electric-400" />}>
            {!tl ? <p className="text-sm text-slate-500">{t("results.noTimeline")}</p> : (<>
              <ol className="relative ml-2 space-y-4 border-l border-white/10 pl-5">
                {tl.events.map((e, i) => (
                  <li key={i} className="relative">
                    <span className={`absolute -left-[26px] top-1 h-2.5 w-2.5 rounded-full ring-4 ring-ink-900 ${KIND_STYLE[e.kind]}`} />
                    <div className="font-mono text-xs text-white">{e.time}</div>
                    <div className="break-words text-xs text-slate-300"><span className="text-slate-500">{e.source_key ? tk(`tlSource.${e.source_key}`, e.source) : e.source} ·</span> {e.field_msg ? tm(e.field_msg, e.field) : e.field}</div>
                    <div className="text-[11px] text-slate-500">{tm(e.meaning_msg, e.meaning)}{e.kind !== "scan" && ` ${t("results.timezone", { tz: e.tz ? t(`tz.${e.tz}`) : e.timezone })}`}</div>
                  </li>
                ))}
              </ol>
              <div className="mt-5 space-y-2">
                <div className="label">{t("results.checks")}</div>
                {tl.checks.map((c) => { const cs = CHECK_STYLE[c.status]; const I = cs.icon; return (
                  <div key={c.id} className="rounded-lg bg-ink-850 p-3">
                    <div className={`flex items-start gap-1.5 text-sm font-medium ${cs.cls}`}><I size={14} className="mt-0.5 shrink-0" /> {tm(c.title_msg, c.title)}</div>
                    <div className="mt-0.5 break-words text-xs text-slate-300">{tm(c.detail_msg, c.detail)}</div>
                    <div className="mt-1 text-[11px] text-slate-500">{tm(c.meaning_msg, c.meaning)}</div>
                  </div>
                ); })}
              </div>
            </>)}
          </Card>
          <div className="min-w-0 space-y-4">
            <Card title={t("results.visual")} icon={<Eye size={15} className="text-electric-400" />}>
              <div className="mb-3 flex flex-wrap gap-2">
                {visKeys.map((k) => <button key={k} onClick={() => setVis(k)} className={`chip border ${vis === k ? "border-electric-500 bg-electric-500/15 text-electric-200" : "border-white/10 text-slate-400 hover:text-white"}`}>{t(`results.vis.${k}`)}</button>)}
              </div>
              <div className="overflow-hidden rounded-xl bg-ink-850"><img src={r.visuals[vis]} alt={t(`results.vis.${vis}`)} className="mx-auto max-h-[420px] object-contain" /></div>
              <p className="mt-2 text-xs text-slate-500">{t(`results.visNote.${vis}`)}</p>
              {r.saliency.status === "ok" && !r.saliency.meaningful && <p className="mt-1 text-xs text-slate-500">{t("results.saliencyNotLocal")}</p>}
            </Card>
            <Card title={t("results.faceAnalysis")} icon={<ScanFace size={15} className="text-electric-400" />}>
              <p className="break-words text-xs text-slate-400">{t("results.faceDetector", { name: r.faces.detector ?? t("common.unavailable") })} · {t("results.faceClassifier", { name: r.faces.manipulation_classifier ?? t("common.unavailable") })}</p>
              {r.faces.faces.length === 0 ? <p className="mt-2 text-sm text-slate-500">{t("results.noFaces")}</p> : (
                <div className="mt-2 overflow-x-auto"><table className="w-full text-left text-xs">
                  <thead className="text-slate-500"><tr><th className="py-1.5">#</th><th>{t("results.colBox")}</th><th>{t("results.colDet")}</th><th>{t("results.colManip")}</th><th /></tr></thead>
                  <tbody className="divide-y divide-white/5">{r.faces.faces.map((f) => (
                    <tr key={f.id}><td className="py-1.5 font-mono">{f.id}</td><td className="font-mono">{f.box.join(",")}</td><td className="font-mono">{f.detection_confidence ?? "—"}</td>
                      <td className="font-mono">{f.manipulation_score ?? (f.note_key ? t(f.note_key) : f.note)}</td><td>{f.flagged ? <span className="chip bg-rose-500/10 text-rose-300">{t("results.flagged")}</span> : null}</td></tr>
                  ))}</tbody></table></div>
              )}
            </Card>
          </div>
        </div>
      </Block>

      {/* 4. Metadata */}
      <Block id="metadata" num={4} title={t("results.sections.metadata")} icon={<Fingerprint size={14} />}>
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title={t("results.evidenceItemCard")}>
            <KV rows={[
              [t("results.caseId"), <span className="font-mono">{r.scan_id}</span>], [t("results.filename"), r.filename], [t("results.received"), fmtDate(r.created_at)],
              [t("results.format"), `${r.file.format} · ${r.file.mime} · ${r.file.mode}`], [t("results.dimensions"), `${r.file.width} × ${r.file.height} px`],
              [t("results.size"), `${fmtBytes(r.file.size_bytes)} (${t("results.bytes", { n: r.file.size_bytes.toLocaleString() })})`],
              ["SHA-256", <span className="break-all font-mono text-[11px]">{r.file.sha256}</span>],
              [t("results.jpegQ"), r.signal.jpeg ? t("results.jpegTables", { q: r.signal.jpeg.estimated_quality, n: r.signal.jpeg.tables }) : t("common.na")],
              [t("results.ela"), t("results.elaValue", { mean: r.signal.ela.mean_error, p99: r.signal.ela.p99_error, nu: r.signal.ela.block_nonuniformity })],
              [t("results.noise"), r.signal.stats.noise_residual_std], [t("results.sharpness"), r.signal.stats.sharpness_laplacian_var],
              [t("results.processing"), <span className="font-mono text-[11px]">{(r.processing_ms / 1000).toFixed(2)} s — {r.stages.map((s) => `${tk(`stage.${s.stage}`, s.stage)} ${s.ms} ms`).join(" · ")}</span>],
            ]} />
          </Card>
          <Card title={t("results.embedded")}>
            <KV rows={[
              [t("results.exif"), m.exif_present ? t("results.exifFields", { n: Object.keys(m.exif).length }) : t("results.none")],
              [t("results.camera"), m.camera ? [m.camera.make, m.camera.model, m.camera.lens].filter(Boolean).join(" · ") : "—"],
              [t("results.software"), m.software ?? "—"], [t("results.creatorTool"), tl?.creator_tool ?? "—"],
              [t("results.editSw"), m.editing_software_detected.join(", ") || t("results.noneDetected")],
              [t("results.xmp"), m.xmp_present ? (m.edit_history_in_xmp ? t("results.xmpWithHistory") : t("results.xmpPresent")) : t("results.none")],
              [t("results.tzOffsets"), tl && Object.keys(tl.timezone_offsets).length ? Object.entries(tl.timezone_offsets).map(([k, v]) => `${k} ${v}`).join(", ") : "—"],
              [t("results.aiMarkers"), markers || t("results.noneDetected")],
              [t("results.c2pa"), `${m.c2pa.present ? t("results.c2paPresent") : t("results.c2paNotFound")} (${m.c2pa.reader})`],
              [t("results.exiftool"), m.exiftool ? t("results.exiftoolTags", { n: Object.keys(m.exiftool).length }) : t("results.exiftoolMissing")],
            ]} />
            {m.exif_present && <details className="mt-3 text-xs"><summary className="cursor-pointer text-electric-400">{t("results.rawExif")}</summary>
              <pre className="mt-2 max-h-56 overflow-auto rounded-lg bg-ink-850 p-3 font-mono text-[11px] text-slate-300">{JSON.stringify(m.exif, null, 2)}</pre></details>}
            {Object.keys(m.png_text_chunks).length > 0 && <details className="mt-3 text-xs"><summary className="cursor-pointer text-electric-400">{t("results.pngChunks")}</summary>
              <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded-lg bg-ink-850 p-3 font-mono text-[11px] text-slate-300">{JSON.stringify(m.png_text_chunks, null, 2)}</pre></details>}
          </Card>
          <Card title={t("results.models")}>
            <div className="space-y-2">{r.detectors.map((d) => (
              <div key={d.key} className="text-xs"><div className="break-all font-mono text-white">{d.model}</div>
                <div className="text-slate-500">{d.architecture} · {d.license} · {d.status}{d.device ? ` · ${d.device}` : ""}{d.inference_ms ? ` · ${d.inference_ms} ms` : ""}</div></div>
            ))}
              <div className="text-xs"><div className="font-mono text-white">{r.faces.detector ?? t("results.faceDetUnavailable")}</div><div className="text-slate-500">{t("results.faceLoc")}</div></div>
              {r.faces.manipulation_classifier && <div className="text-xs"><div className="break-all font-mono text-white">{r.faces.manipulation_classifier}</div><div className="text-slate-500">{t("results.faceManipModel")}</div></div>}
            </div>
          </Card>
        </div>
      </Block>

      {/* 5. Limitations */}
      <Block id="limitations" num={5} title={t("results.sections.limitations")} icon={<AlertTriangle size={14} />}>
        <div className="rounded-2xl border border-amber-500/20 bg-amber-500/[0.04] p-5">
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-300">{zipMsgs(a.limitations_msgs, a.limitations).map(({ msg, txt }) => <li key={txt}>{tm(msg, txt)}</li>)}</ul>
          <p className="mt-4 text-xs text-slate-500">{tm(a.method_msg, a.method)}</p>
        </div>
      </Block>
    </div>
  );
}
