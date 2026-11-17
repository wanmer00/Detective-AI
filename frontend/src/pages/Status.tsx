import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { useHealth } from "../components/Layout";
import { Section } from "../components/ui";
import { useI18n } from "../i18n";

const Dot = ({ ok }: { ok: boolean }) => ok ? <CheckCircle2 size={16} className="shrink-0 text-emerald-400" /> : <XCircle size={16} className="shrink-0 text-rose-400" />;

export default function Status() {
  const { t } = useI18n();
  const { h, err } = useHealth();
  if (err) return <div className="card card-pad text-rose-300"><XCircle className="mb-2" /> {t("status.unreachable", { cmd: "start-backend.ps1" })}</div>;
  if (!h) return <div className="flex items-center gap-2 py-20 text-slate-400"><Loader2 className="animate-spin" size={18} /> {t("status.running")}</div>;
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <div className="label">{t("status.label")}</div>
        <h1 className="mt-1 text-2xl font-semibold text-white">{t("status.title")} <span className={h.status === "ready" ? "text-emerald-300" : "text-amber-300"}>{t(`status.${h.status}`)}</span></h1>
      </div>
      <Section title={t("status.core")}>
        <ul className="space-y-2 text-sm">
          <li className="flex items-center gap-2"><Dot ok={h.backend} /> {t("status.backend")}</li>
          <li className="flex items-center gap-2"><Dot ok={h.database} /> {t("status.database")}</li>
          <li className="flex items-center gap-2"><Dot ok={h.models_loaded} /> {t("status.modelsLoaded")}</li>
          <li className="flex items-center gap-2"><Dot ok={h.detector_ready} /> {t("status.detectorReady")}</li>
          <li className="flex items-start gap-2"><Dot ok={!!h.face_detector} /> {t("status.faceDetector", { name: h.face_detector ?? t("common.unavailable") })}</li>
          <li className="flex items-start gap-2"><Dot ok={!!h.gpu} /> {t("status.gpu", { name: h.gpu ?? t("status.cpuOnly") })}</li>
          <li className="flex items-start gap-2"><Dot ok={h.offline_mode} /> {t("status.offline")}</li>
        </ul>
      </Section>
      <Section title={t("status.models")}>
        <ul className="space-y-2 text-sm">{h.models.map((m) => (
          <li key={m.key} className="flex items-start gap-2"><Dot ok={m.available} /><div className="min-w-0"><div className="break-all font-mono text-xs text-white">{m.model}</div><div className="text-xs text-slate-500">{m.license} · {m.available ? m.device : m.error}</div></div></li>
        ))}</ul>
      </Section>
      <Section title={t("status.deps")}>
        <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">{Object.entries(h.dependencies).map(([k, v]) => <div key={k} className="flex items-center gap-2"><Dot ok={v} /> {k}</div>)}</div>
        <p className="mt-3 text-xs text-slate-500">{t("status.depsNote", { py: h.python, mb: h.max_upload_mb })}</p>
      </Section>
    </div>
  );
}
