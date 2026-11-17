import { Languages } from "lucide-react";
import { LANGS, useI18n } from "../i18n";

/** EN / RU / AZ segmented control. Switches instantly; the choice is kept in localStorage. */
export default function LanguageSwitcher({ className = "" }: { className?: string }) {
  const { lang, setLang, t } = useI18n();
  return (
    <div role="group" aria-label={t("lang.label")} className={`flex items-center gap-1 rounded-full border border-white/10 bg-ink-900/60 p-0.5 ${className}`}>
      <Languages size={13} className="ml-1.5 text-slate-500" aria-hidden />
      {LANGS.map((l) => (
        <button
          key={l}
          onClick={() => setLang(l)}
          aria-pressed={lang === l}
          title={t(`lang.name_${l}`)}
          className={`rounded-full px-2 py-0.5 font-mono text-[11px] font-medium transition ${lang === l ? "bg-electric-500 text-white shadow-[0_0_12px_-4px_rgba(47,129,247,0.9)]" : "text-slate-400 hover:text-white"}`}
        >
          {t(`lang.${l}`)}
        </button>
      ))}
    </div>
  );
}
