import { AlertTriangle, Bot, Camera, HelpCircle, Layers, ScanLine, ShieldCheck, Wand2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Empty, Section, VerdictBadge } from "../components/ui";
import { errorText, useI18n } from "../i18n";
import { api } from "../services/api";
import type { Stats } from "../types";

export default function Dashboard() {
  const { t, fmtDate } = useI18n();
  const [s, setS] = useState<Stats | null>(null);
  const [err, setErr] = useState<unknown>(null);
  useEffect(() => { api.stats().then(setS).catch(setErr); }, []);
  const tiles = s ? [
    { k: "total", v: s.total, i: Layers, c: "text-electric-400" },
    { k: "ai", v: s.ai_likely, i: Bot, c: "text-rose-300" },
    { k: "aiEdited", v: s.ai_edited ?? 0, i: Wand2, c: "text-fuchsia-300" },
    { k: "authentic", v: s.authentic_likely, i: Camera, c: "text-emerald-300" },
    { k: "notAi", v: s.not_ai, i: ShieldCheck, c: "text-sky-300" },
    { k: "manip", v: s.manipulated_possible, i: AlertTriangle, c: "text-amber-300" },
    { k: "inconclusive", v: s.inconclusive, i: HelpCircle, c: "text-slate-300" },
  ] : [];
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="label">{t("dashboard.label")}</div>
          <h1 className="mt-1 text-2xl font-semibold text-white">{t("dashboard.title")}</h1>
          <p className="mt-1 text-sm text-slate-400">{t("dashboard.subtitle")}</p>
        </div>
        <Link to="/scan" className="btn-primary"><ScanLine size={16} /> {t("dashboard.newAnalysis")}</Link>
      </div>
      {err != null && <div className="card card-pad text-sm text-rose-300">{t("dashboard.loadError", { error: errorText(t, err) })}</div>}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-7">
        {tiles.map((x) => (
          <div key={x.k} className="card card-pad">
            <x.i size={18} className={x.c} />
            <div className="mt-3 text-3xl font-semibold tabular-nums text-white">{x.v}</div>
            <div className="mt-1 text-xs leading-snug text-slate-400">{t(`dashboard.tiles.${x.k}`)}</div>
          </div>
        ))}
      </div>
      <Section title={t("dashboard.recent")} right={<Link to="/history" className="text-xs text-electric-400 hover:underline">{t("dashboard.viewAll")}</Link>}>
        {s && s.recent.length === 0 ? (
          <Empty>{t("dashboard.empty")} <Link to="/scan" className="text-electric-400">{t("dashboard.emptyCta")}</Link>.</Empty>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {s?.recent.map((r) => (
              <Link key={r.scan_id} to={`/results/${r.scan_id}`} className="flex min-w-0 gap-3 rounded-xl border border-white/5 bg-ink-850 p-3 transition hover:border-electric-500/30">
                <img src={r.thumbnail} alt="" className="h-16 w-16 shrink-0 rounded-lg object-cover" />
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-white">{r.filename}</div>
                  <div className="mt-0.5 font-mono text-[11px] text-slate-500">{r.scan_id}</div>
                  <div className="mt-1.5 flex min-w-0 flex-wrap items-center gap-2"><VerdictBadge verdict={r.verdict} />
                    {r.ai_likelihood != null ? <span className="font-mono text-[11px] text-slate-400">{t("dashboard.aiScore", { score: r.ai_likelihood.toFixed(2) })}</span>
                      : r.detection_confidence && <span className="text-[11px] text-slate-400">{t("dashboard.confidence", { level: t(`confidence.${r.detection_confidence}`) })}</span>}</div>
                  <div className="mt-1 text-[11px] text-slate-500">{fmtDate(r.created_at)}</div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}
