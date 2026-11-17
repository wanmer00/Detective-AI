import { Download, Loader2, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Empty, VerdictBadge } from "../components/ui";
import { errorText, useI18n } from "../i18n";
import { api } from "../services/api";
import type { ScanSummary, Verdict } from "../types";

const FILTERS: ("" | Verdict)[] = ["", "ai_likely", "ai_edited", "authentic_likely", "not_ai", "manipulated_possible", "inconclusive"];

export default function HistoryPage() {
  const { t, lang, fmtDate } = useI18n();
  const [q, setQ] = useState("");
  const [verdict, setVerdict] = useState("");
  const [rows, setRows] = useState<ScanSummary[] | null>(null);
  const [err, setErr] = useState<unknown>(null);
  const [confirm, setConfirm] = useState<string | null>(null);

  const load = () => api.scans(q, verdict).then((x) => { setRows(x); setErr(null); }).catch(setErr);
  useEffect(() => { const id = setTimeout(load, 250); return () => clearTimeout(id); }, [q, verdict]); // eslint-disable-line

  async function del(id: string) {
    try { await api.remove(id); setConfirm(null); load(); } catch (e) { setErr(e); }
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="label">{t("history.label")}</div>
        <h1 className="mt-1 text-2xl font-semibold text-white">{t("history.title")}</h1>
      </div>
      <div className="flex flex-col gap-3 md:flex-row">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input className="input pl-9" placeholder={t("history.search")} value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((v) => (
            <button key={v} onClick={() => setVerdict(v)} className={`chip border px-3 py-1.5 ${verdict === v ? "border-electric-500 bg-electric-500/15 text-electric-200" : "border-white/10 text-slate-400 hover:text-white"}`}>
              {v ? t(`verdictShort.${v}`) : t("history.all")}
            </button>
          ))}
        </div>
      </div>
      {err != null && <div className="card card-pad text-sm text-rose-300">{errorText(t, err)}</div>}
      <div className="card overflow-hidden">
        {rows === null ? <div className="flex items-center gap-2 p-6 text-sm text-slate-400"><Loader2 size={16} className="animate-spin" /> {t("common.loading")}</div> :
          rows.length === 0 ? <Empty>{t("history.empty")}</Empty> : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="border-b border-white/5 text-xs text-slate-500"><tr>
                  <th className="px-4 py-3">{t("history.cols.image")}</th><th>{t("history.cols.assessment")}</th><th>{t("history.cols.aiScore")}</th>
                  <th>{t("history.cols.evidence")}</th><th>{t("history.cols.type")}</th><th>{t("history.cols.date")}</th><th className="px-4 text-right">{t("history.cols.actions")}</th></tr></thead>
                <tbody className="divide-y divide-white/5">
                  {rows.map((r) => (
                    <tr key={r.scan_id} className="hover:bg-white/[0.02]">
                      <td className="px-4 py-3"><Link to={`/results/${r.scan_id}`} className="flex items-center gap-3">
                        <img src={r.thumbnail} alt="" className="h-10 w-10 shrink-0 rounded-lg object-cover" />
                        <div className="min-w-0"><div className="max-w-[220px] truncate text-white">{r.filename}</div><div className="font-mono text-[11px] text-slate-500">{r.scan_id}{r.is_demo && ` · ${t("history.demo")}`}</div></div>
                      </Link></td>
                      <td className="max-w-[200px]"><VerdictBadge verdict={r.verdict} /></td>
                      <td className="text-xs">{r.ai_likelihood != null ? <span className="font-mono">{r.ai_likelihood.toFixed(3)}</span>
                        : r.detection_confidence ? <span className="text-slate-300">{t(`confidence.${r.detection_confidence}`)}</span> : "—"}</td>
                      <td className="text-xs text-slate-400">{t(`evidenceStrength.${r.evidence_strength}`)}</td>
                      <td className="whitespace-nowrap text-xs text-slate-400">{r.file_type} {r.width}×{r.height}</td>
                      <td className="text-xs text-slate-400">{fmtDate(r.created_at)}</td>
                      <td className="px-4 text-right">
                        <div className="flex justify-end gap-1">
                          <a href={api.pdfUrl(r.scan_id, lang)} className="rounded-lg p-2 text-slate-400 hover:bg-white/5 hover:text-white" title={t("history.downloadPdf")} aria-label={t("history.downloadPdf")}><Download size={15} /></a>
                          {confirm === r.scan_id ? (
                            <><button onClick={() => del(r.scan_id)} className="rounded-lg bg-rose-500/20 px-2 text-xs text-rose-200" title={t("history.confirmDelete")}>{t("common.delete")}</button>
                              <button onClick={() => setConfirm(null)} className="rounded-lg px-2 text-xs text-slate-400">{t("common.cancel")}</button></>
                          ) : <button onClick={() => setConfirm(r.scan_id)} className="rounded-lg p-2 text-slate-400 hover:bg-rose-500/10 hover:text-rose-300" title={t("history.deleteScan")} aria-label={t("history.deleteScan")}><Trash2 size={15} /></button>}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </div>
    </div>
  );
}
