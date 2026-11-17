import { AlertTriangle, Bot, Camera, HelpCircle, ScanSearch, ShieldCheck, Wand2 } from "lucide-react";
import type { ReactNode } from "react";
import { useI18n } from "../i18n";
import type { Verdict } from "../types";

export function Logo({ size = 28 }: { size?: number }) {
  return (
    <div className="flex items-center gap-2.5">
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
        <rect width="32" height="32" rx="8" fill="#0E1526" stroke="rgba(90,169,255,.35)" />
        <circle cx="14" cy="14" r="7" fill="none" stroke="#2F81F7" strokeWidth="2.5" />
        <path d="M19 19l6 6" stroke="#5AA9FF" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx="14" cy="14" r="2.5" fill="#8CC4FF" />
      </svg>
      <span className="text-[15px] font-semibold tracking-tight text-white">
        Detective <span className="text-electric-400">AI</span>
      </span>
    </div>
  );
}

export const VERDICT_META: Record<Verdict, { color: string; bg: string; ring: string; icon: typeof Bot }> = {
  ai_likely: { color: "text-rose-300", bg: "bg-rose-500/10", ring: "ring-rose-500/30", icon: Bot },
  ai_edited: { color: "text-fuchsia-300", bg: "bg-fuchsia-500/10", ring: "ring-fuchsia-500/30", icon: Wand2 },
  authentic_likely: { color: "text-emerald-300", bg: "bg-emerald-500/10", ring: "ring-emerald-500/30", icon: Camera },
  not_ai: { color: "text-sky-300", bg: "bg-sky-500/10", ring: "ring-sky-500/30", icon: ShieldCheck },
  manipulated_possible: { color: "text-amber-300", bg: "bg-amber-500/10", ring: "ring-amber-500/30", icon: AlertTriangle },
  inconclusive: { color: "text-slate-300", bg: "bg-slate-500/10", ring: "ring-slate-500/30", icon: HelpCircle },
};

/** Verdict chip. `full` shows the full verdict text instead of the short label. */
export function VerdictBadge({ verdict, full = false }: { verdict: Verdict; full?: boolean }) {
  const { t } = useI18n();
  const m = VERDICT_META[verdict] ?? VERDICT_META.inconclusive;
  const Icon = m.icon;
  return (
    <span className={`chip ring-1 ${m.bg} ${m.color} ${m.ring} max-w-full`}>
      <Icon size={12} className="shrink-0" /> <span className="truncate">{t(full ? `verdict.${verdict}` : `verdictShort.${verdict}`)}</span>
    </span>
  );
}

export function ScoreBar({ value, label }: { value: number | null | undefined; label?: string }) {
  const { t } = useI18n();
  if (value == null) return <div className="text-sm text-slate-500">{t("common.unavailable")}</div>;
  const pct = Math.round(value * 100);
  const color = value >= 0.8 ? "bg-rose-400" : value <= 0.2 ? "bg-emerald-400" : "bg-amber-400";
  return (
    <div>
      {label && <div className="mb-1 flex justify-between text-xs text-slate-400"><span>{label}</span><span className="font-mono">{value.toFixed(3)}</span></div>}
      <div className="h-2 rounded-full bg-white/5">
        <div className={`h-2 rounded-full ${color} transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function Section({ title, icon, children, right }: { title: string; icon?: ReactNode; children: ReactNode; right?: ReactNode }) {
  return (
    <section className="card card-pad fade-up">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-white">{icon}{title}</h3>
        {right}
      </div>
      {children}
    </section>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-sm text-slate-500">
      <ScanSearch className="text-slate-600" />
      {children}
    </div>
  );
}

export function Strength({ s }: { s: string }) {
  const { t } = useI18n();
  const c = s === "strong" ? "bg-electric-500/20 text-electric-300" : s === "moderate" ? "bg-white/10 text-slate-200" : "bg-white/5 text-slate-400";
  return <span className={`chip ${c} shrink-0`}>{t(`strength.${s}`)}</span>;
}

export const fmtBytes = (n: number) => (n > 1048576 ? `${(n / 1048576).toFixed(2)} MB` : `${(n / 1024).toFixed(1)} KB`);
