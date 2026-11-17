import { AlertCircle, FlaskConical, ImageUp, Loader2, RefreshCw, ScanLine, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fmtBytes, Section } from "../components/ui";
import { errorText, useI18n } from "../i18n";
import { api } from "../services/api";
import type { Sample } from "../types";

const EXTS = ["jpg", "jpeg", "png", "webp", "heic", "heif", "avif"];
const NO_PREVIEW_OK = ["heic", "heif", "avif"];
const extOf = (name: string) => (name.includes(".") ? name.split(".").pop()!.toLowerCase() : "");
const MAX_MB = 15;
const PIPELINE = ["validate", "metadata", "detect", "saliency", "ela", "faces", "aggregate"];

export default function Scanner() {
  const { t, tk } = useI18n();
  const nav = useNavigate();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [dims, setDims] = useState<[number, number] | null>(null);
  const [drag, setDrag] = useState(false);
  // Errors are stored as data and rendered at display time, so they follow language switches.
  const [err, setErr] = useState<{ key: string; params?: Record<string, unknown> } | { error: unknown } | null>(null);
  const [busy, setBusy] = useState(false);
  const [upload, setUpload] = useState(0);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [tick, setTick] = useState(0);

  useEffect(() => { api.samples().then(setSamples).catch(() => setSamples([])); }, []);
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);
  useEffect(() => {
    if (!busy) return;
    const id = setInterval(() => setTick((x) => x + 1), 900);
    return () => clearInterval(id);
  }, [busy]);

  function pick(f: File | undefined) {
    setErr(null);
    if (!f) return;
    const ext = extOf(f.name);
    if (!EXTS.includes(ext)) return setErr({ key: "errors.unsupportedType" });
    if (f.size > MAX_MB * 1048576) return setErr({ key: "errors.fileTooBig", params: { size: fmtBytes(f.size), mb: MAX_MB } });
    const u = URL.createObjectURL(f);
    const img = new Image();
    img.onload = () => { setDims([img.naturalWidth, img.naturalHeight]); setFile(f); setUrl(u); };
    img.onerror = () => {
      URL.revokeObjectURL(u);
      // Most browsers cannot display HEIC (iPhone) files; the server can still decode and analyse them.
      if (NO_PREVIEW_OK.includes(ext)) { setDims(null); setFile(f); setUrl(null); }
      else setErr({ key: "errors.browserDecode" });
    };
    img.src = u;
  }
  function clear() { setFile(null); setUrl(null); setDims(null); setErr(null); setUpload(0); if (input.current) input.current.value = ""; }

  async function run(fn: () => Promise<{ scan_id: string }>) {
    setBusy(true); setErr(null); setTick(0);
    try { const r = await fn(); nav(`/results/${r.scan_id}`); }
    catch (e) { setErr({ error: e }); }
    finally { setBusy(false); }
  }

  const errMsg = err == null ? "" : "key" in err ? t(err.key, err.params) : errorText(t, err.error);
  const uploading = busy && file && upload < 100;
  return (
    <div className="space-y-6">
      <div>
        <div className="label">{t("scanner.label")}</div>
        <h1 className="mt-1 text-2xl font-semibold text-white">{t("scanner.title")}</h1>
        <p className="mt-1 text-sm text-slate-400">{t("scanner.subtitle", { mb: MAX_MB })}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="card card-pad min-w-0">
          {!file ? (
            <div
              onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); }}
              onClick={() => input.current?.click()}
              role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && input.current?.click()}
              className={`flex min-h-[340px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-4 text-center transition ${drag ? "border-electric-400 bg-electric-500/10" : "border-white/10 hover:border-electric-500/50 hover:bg-white/[0.02]"}`}
            >
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-electric-500/10"><ImageUp className="text-electric-400" /></div>
              <div className="mt-4 font-medium text-white">{t("scanner.drop")}</div>
              <div className="mt-1 text-sm text-slate-400">{t("scanner.or")} <span className="text-electric-400">{t("scanner.browse")}</span></div>
            </div>
          ) : (
            <div>
              <div className="relative overflow-hidden rounded-xl bg-ink-850">
                {url ? <img src={url} alt={t("scanner.previewAlt")} className="mx-auto max-h-[460px] object-contain" /> : (
                  <div className="flex min-h-[260px] flex-col items-center justify-center gap-2 px-4 text-center text-sm text-slate-400">
                    <ImageUp className="text-electric-400" />
                    <span>{t("scanner.noPreview", { ext: extOf(file.name).toUpperCase() })}</span>
                    <span className="text-xs text-slate-500">{t("scanner.noPreviewNote")}</span>
                  </div>
                )}
                {busy && <div className="pointer-events-none absolute inset-0 overflow-hidden"><div className="scanline h-1/3 w-full bg-gradient-to-b from-transparent via-electric-400/25 to-transparent" /></div>}
              </div>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0 text-sm">
                  <div className="truncate font-medium text-white">{file.name}</div>
                  <div className="font-mono text-xs text-slate-400">{extOf(file.name).toUpperCase()}{dims ? ` · ${dims[0]}×${dims[1]} px` : ""} · {fmtBytes(file.size)}</div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button className="btn-ghost" disabled={busy} onClick={() => input.current?.click()}><RefreshCw size={15} /> {t("scanner.replace")}</button>
                  <button className="btn-ghost" disabled={busy} onClick={clear}><Trash2 size={15} /> {t("scanner.remove")}</button>
                  <button className="btn-primary" disabled={busy} onClick={() => run(() => api.analyze(file, setUpload))}>
                    {busy ? <Loader2 size={16} className="animate-spin" /> : <ScanLine size={16} />} {t("scanner.analyze")}
                  </button>
                </div>
              </div>
            </div>
          )}
          <input ref={input} type="file" accept=".jpg,.jpeg,.png,.webp,.heic,.heif,.avif,image/jpeg,image/png,image/webp,image/heic,image/heif,image/avif" className="hidden" onChange={(e) => pick(e.target.files?.[0])} />
          {errMsg && <div className="mt-4 flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-200"><AlertCircle size={16} className="mt-0.5 shrink-0" /> {errMsg}</div>}
        </div>

        <div className="min-w-0 space-y-6">
          <Section title={t("scanner.progress")}>
            {!busy ? <p className="text-sm text-slate-500">{t("scanner.idle")}</p> : (
              <div className="space-y-3">
                {file && (
                  <div>
                    <div className="mb-1 flex justify-between text-xs text-slate-400"><span>{t("scanner.upload")}</span><span className="font-mono">{upload}%</span></div>
                    <div className="h-1.5 rounded-full bg-white/5"><div className="h-1.5 rounded-full bg-electric-500 transition-all" style={{ width: `${upload}%` }} /></div>
                  </div>
                )}
                <div className="flex items-center gap-2 text-sm text-electric-300">
                  <Loader2 size={15} className="shrink-0 animate-spin" /> {uploading ? t("scanner.uploading") : t("scanner.inProgress", { s: tick })}
                </div>
                <ul className="space-y-1.5 text-xs text-slate-400">
                  {PIPELINE.map((p) => <li key={p} className="flex items-center gap-2"><span className="h-1.5 w-1.5 shrink-0 rounded-full bg-electric-500/60" />{t(`scanner.stages.${p}`)}</li>)}
                </ul>
                <p className="text-[11px] text-slate-500">{t("scanner.timingsNote")}</p>
              </div>
            )}
          </Section>
          <Section title={t("scanner.samples")} icon={<FlaskConical size={15} className="text-electric-400" />}>
            {samples.length === 0 ? <p className="text-sm text-slate-500">{t("scanner.noSamples")}</p> : (
              <div className="space-y-2">
                {samples.map((s) => (
                  <button key={s.id} disabled={busy} onClick={() => run(() => api.analyzeSample(s.id))}
                    className="flex w-full items-center gap-3 rounded-xl border border-white/5 bg-ink-850 p-2.5 text-left transition hover:border-electric-500/40 disabled:opacity-50">
                    <img src={s.thumbnail} alt="" className="h-12 w-12 shrink-0 rounded-lg object-cover" />
                    <div className="min-w-0">
                      <div className="line-clamp-2 text-sm leading-snug text-white">{tk(`samples.${s.id}.title`, s.title)}</div>
                      <div className="truncate text-[11px] text-slate-500">{tk(`samples.${s.id}.category`, s.category)} · {s.license}</div>
                    </div>
                  </button>
                ))}
                <p className="pt-1 text-[11px] text-slate-500">{t("scanner.samplesNote")}</p>
              </div>
            )}
          </Section>
        </div>
      </div>
    </div>
  );
}
