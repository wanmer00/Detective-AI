import { Section } from "../components/ui";
import { Rich, useI18n } from "../i18n";

const MODELS = [
  { name: "haywoodsloan/ai-image-detector-deploy", d: "m1d", r: "m1r", lic: "Apache-2.0" },
  { name: "Thermostatic/community-forensics-frontier-detector-2026-08", d: "m4d", r: "m4r", lic: "MIT" },
  { name: "Thermostatic/community-forensics-low-quality-detector-2026-08", d: "m5d", r: "m5r", lic: "MIT" },
  { name: "prithivMLmods/Deep-Fake-Detector-v2-Model", d: "m2d", r: "m2r", lic: "Apache-2.0" },
  { name: "OpenCV YuNet (2023mar)", d: "m3d", r: "m3r", lic: "Apache-2.0" },
];
const RULES = ["R1", "R1e", "R2", "R2e", "R3", "R4", "R4b", "R5", "R6", "R7", "R8", "R9"];

export default function About() {
  const { t } = useI18n();
  const list = (prefix: string, keys: string[]) => (
    <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-400">{keys.map((k) => <li key={k}><Rich text={t(`${prefix}.${k}`)} /></li>)}</ul>
  );
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <div className="label">{t("about.label")}</div>
        <h1 className="mt-1 text-2xl font-semibold text-white">{t("about.title")}</h1>
      </div>
      <Section title={t("about.detectorsTitle")}>
        <p className="text-sm leading-relaxed text-slate-400"><Rich text={t("about.detectorsP1")} /></p>
        <p className="mt-3 text-sm leading-relaxed text-slate-400"><Rich text={t("about.detectorsP3")} /></p>
        <p className="mt-3 text-sm leading-relaxed text-slate-400"><Rich text={t("about.detectorsP2")} /></p>
      </Section>
      <Section title={t("about.forensicsTitle")}>{list("about.forensics", ["f1", "f2", "f3", "f4", "f5"])}</Section>
      <Section title={t("about.rulesTitle")}>
        <p className="text-sm text-slate-400">{t("about.rulesText")}</p>
        <ul className="mt-3 space-y-1 font-mono text-xs text-slate-400">{RULES.map((r) => <li key={r}>{t(`about.rules.${r}`)}</li>)}</ul>
      </Section>
      <Section title={t("about.notDefTitle")}>{list("about.notDef", ["n1", "n2", "n3", "n4", "n5"])}</Section>
      <Section title={t("about.modelsTitle")}>
        <div className="overflow-x-auto"><table className="w-full min-w-[560px] text-left text-sm">
          <thead className="text-xs text-slate-500"><tr><th className="py-2">{t("about.cols.model")}</th><th>{t("about.cols.description")}</th><th>{t("about.cols.license")}</th><th>{t("about.cols.role")}</th></tr></thead>
          <tbody className="divide-y divide-white/5 text-slate-300">{MODELS.map((m) => (
            <tr key={m.name}><td className="py-2 pr-3 font-mono text-xs">{m.name}</td><td className="pr-3 text-xs text-slate-400">{t(`about.models.${m.d}`)}</td><td className="pr-3 text-xs">{m.lic}</td><td className="text-xs">{t(`about.models.${m.r}`)}</td></tr>
          ))}</tbody>
        </table></div>
      </Section>
      <Section title={t("about.privacyTitle")}>{list("about.privacy", ["p1", "p2", "p3", "p4", "p5"])}</Section>
    </div>
  );
}
