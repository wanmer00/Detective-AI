import { ArrowRight, Cpu, FileSearch, FileText, Fingerprint, Lock, ScanFace, ShieldAlert, Sparkles, Upload, Workflow } from "lucide-react";
import { Link } from "react-router-dom";
import LanguageSwitcher from "../components/LanguageSwitcher";
import { Logo } from "../components/ui";
import { useI18n } from "../i18n";

const STEPS = [
  { icon: Upload, k: "upload" }, { icon: Cpu, k: "analyse" }, { icon: Workflow, k: "aggregate" }, { icon: FileText, k: "report" },
];
const CAPS = [
  { icon: Sparkles, k: "ai" }, { icon: FileSearch, k: "meta" }, { icon: Fingerprint, k: "c2pa" },
  { icon: ShieldAlert, k: "ela" }, { icon: ScanFace, k: "faces" }, { icon: Cpu, k: "saliency" },
];
const TECH = ["i1", "i2", "i3", "i4", "i5", "i6", "i7", "i8"];

export default function Landing() {
  const { t } = useI18n();
  return (
    <div className="min-h-screen overflow-x-hidden bg-ink-950 text-slate-200">
      <div className="grid-bg absolute inset-x-0 top-0 h-[640px] [mask-image:linear-gradient(to_bottom,black,transparent)]" />
      <header className="relative mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
        <Logo />
        <nav className="flex items-center gap-2 text-sm">
          <Link to="/methodology" className="hidden px-3 py-2 text-slate-400 hover:text-white md:block">{t("nav.methodology")}</Link>
          <Link to="/dashboard" className="hidden px-3 py-2 text-slate-400 hover:text-white md:block">{t("nav.dashboard")}</Link>
          <LanguageSwitcher />
          <Link to="/scan" className="btn-primary hidden whitespace-nowrap sm:inline-flex">{t("common.analyzeImage")}</Link>
        </nav>
      </header>

      <section className="relative mx-auto max-w-7xl px-4 pb-20 pt-16 sm:px-6 sm:pt-24">
        <div className="max-w-3xl fade-up">
          <span className="chip border border-electric-500/30 bg-electric-500/10 text-electric-300">
            <Lock size={12} className="shrink-0" /> {t("landing.badge")}
          </span>
          <h1 className="mt-6 text-4xl font-semibold leading-[1.08] tracking-tight text-white sm:text-6xl">
            {t("landing.titleA")}<br /><span className="bg-gradient-to-r from-electric-300 to-electric-500 bg-clip-text text-transparent">{t("landing.titleB")}</span>
          </h1>
          <p className="mt-6 max-w-2xl text-lg text-slate-400">{t("landing.lead")}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/scan" className="btn-primary px-6 py-3 text-base">{t("common.analyzeImage")} <ArrowRight size={18} /></Link>
            <Link to="/methodology" className="btn-ghost px-6 py-3 text-base">{t("common.howItWorks")}</Link>
          </div>
        </div>
      </section>

      <section className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6">
        <div className="label">{t("landing.howLabel")}</div>
        <h2 className="mt-2 text-2xl font-semibold text-white sm:text-3xl">{t("landing.howTitle")}</h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <div key={s.k} className="card card-pad">
              <div className="flex items-center justify-between">
                <s.icon className="text-electric-400" size={22} />
                <span className="font-mono text-xs text-slate-600">0{i + 1}</span>
              </div>
              <div className="mt-4 font-medium text-white">{t(`landing.steps.${s.k}.t`)}</div>
              <p className="mt-1.5 text-sm text-slate-400">{t(`landing.steps.${s.k}.d`)}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6">
        <div className="label">{t("landing.capsLabel")}</div>
        <h2 className="mt-2 text-2xl font-semibold text-white sm:text-3xl">{t("landing.capsTitle")}</h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CAPS.map((c) => (
            <div key={c.k} className="card card-pad transition hover:border-electric-500/30">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-electric-500/10"><c.icon size={20} className="text-electric-400" /></div>
              <div className="mt-4 font-medium text-white">{t(`landing.caps.${c.k}.t`)}</div>
              <p className="mt-1.5 text-sm text-slate-400">{t(`landing.caps.${c.k}.d`)}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6">
        <div className="card card-pad grid gap-8 lg:grid-cols-2">
          <div>
            <div className="label">{t("landing.techLabel")}</div>
            <h2 className="mt-2 text-2xl font-semibold text-white">{t("landing.techTitle")}</h2>
            <p className="mt-3 text-sm text-slate-400">{t("landing.techText")}</p>
          </div>
          <ul className="grid gap-2 font-mono text-xs text-slate-300 sm:grid-cols-2">
            {TECH.map((k) => <li key={k} className="rounded-lg border border-white/5 bg-ink-850 px-3 py-2">{t(`landing.tech.${k}`)}</li>)}
          </ul>
        </div>
      </section>

      <section className="relative mx-auto max-w-7xl px-4 pb-20 sm:px-6">
        <div className="rounded-2xl border border-amber-500/20 bg-amber-500/[0.04] p-6">
          <div className="flex items-center gap-2 font-medium text-amber-200"><ShieldAlert size={18} className="shrink-0" /> {t("landing.disclaimerTitle")}</div>
          <p className="mt-2 text-sm text-slate-400">{t("landing.disclaimer")}</p>
        </div>
      </section>
      <footer className="border-t border-white/[0.06] py-6 text-center text-xs text-slate-500">{t("footer.short")}</footer>
    </div>
  );
}
