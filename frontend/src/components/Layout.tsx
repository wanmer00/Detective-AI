import { Activity, BookOpen, History, LayoutDashboard, Menu, ScanLine, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useI18n } from "../i18n";
import { api } from "../services/api";
import type { Health } from "../types";
import LanguageSwitcher from "./LanguageSwitcher";
import { Logo } from "./ui";

const NAV = [
  { to: "/dashboard", key: "nav.dashboard", icon: LayoutDashboard },
  { to: "/scan", key: "nav.scanner", icon: ScanLine },
  { to: "/history", key: "nav.history", icon: History },
  { to: "/methodology", key: "nav.methodology", icon: BookOpen },
  { to: "/status", key: "nav.status", icon: Activity },
];

export function useHealth() {
  const [h, setH] = useState<Health | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    let alive = true;
    const load = () => api.health().then((x) => alive && (setH(x), setErr(false))).catch(() => alive && setErr(true));
    load();
    const t = setInterval(load, 15000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  return { h, err };
}

function HealthPill() {
  const { t } = useI18n();
  const { h, err } = useHealth();
  const [key, cls] = err ? ["health.offline", "bg-rose-400"] : !h ? ["health.checking", "bg-slate-400"] : h.status === "ready" ? ["health.ready", "bg-emerald-400"] : ["health.degraded", "bg-amber-400"];
  return (
    <Link to="/status" className="flex items-center gap-2 whitespace-nowrap rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300 hover:bg-white/5">
      <span className={`h-2 w-2 shrink-0 rounded-full ${cls} ${h?.status === "ready" ? "animate-pulse" : ""}`} /> {t(key)}
    </Link>
  );
}

export default function Layout() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  useEffect(() => setOpen(false), [loc.pathname]);
  return (
    <div className="min-h-screen bg-ink-950 bg-[radial-gradient(ellipse_at_top,rgba(47,129,247,0.10),transparent_55%)]">
      <header className="sticky top-0 z-30 border-b border-white/[0.06] bg-ink-950/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-4 sm:px-6">
          <Link to="/" className="shrink-0"><Logo /></Link>
          <nav className="hidden min-w-0 items-center gap-1 xl:flex">
            {NAV.map(({ to, key, icon: I }) => (
              <NavLink key={to} to={to} className={({ isActive }) => `flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-sm transition ${isActive ? "bg-white/[0.06] text-white" : "text-slate-400 hover:text-white"}`}>
                <I size={15} /> {t(key)}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-2 sm:gap-3">
            <LanguageSwitcher />
            <div className="hidden xl:block"><HealthPill /></div>
            <button className="rounded-lg p-2 text-slate-300 hover:bg-white/5 xl:hidden" onClick={() => setOpen(!open)} aria-label={t("nav.menu")}>
              {open ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>
        {open && (
          <nav className="border-t border-white/5 px-4 pb-4 xl:hidden">
            {NAV.map(({ to, key, icon: I }) => (
              <NavLink key={to} to={to} className={({ isActive }) => `mt-1 flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm ${isActive ? "bg-white/[0.06] text-white" : "text-slate-400"}`}>
                <I size={16} /> {t(key)}
              </NavLink>
            ))}
            <div className="mt-3"><HealthPill /></div>
          </nav>
        )}
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>
      <footer className="border-t border-white/[0.06] px-4 py-6 text-center text-xs text-slate-500">
        {t("footer.text")}
      </footer>
    </div>
  );
}
