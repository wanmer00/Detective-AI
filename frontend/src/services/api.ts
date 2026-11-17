import { ApiError } from "../i18n";
import type { Lang } from "../i18n";
import type { Health, Report, Sample, ScanSummary, Stats } from "../types";

function toError(status: number, body: any): ApiError {
  const detail = body?.detail;
  const message = typeof detail === "string" ? detail : `Request failed (${status})`;
  return new ApiError(message, body?.code ?? (typeof detail === "string" ? undefined : "requestFailed"), body?.params, status);
}

async function json<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let body: any = null;
    try { body = await r.json(); } catch { /* non-JSON error body */ }
    throw toError(r.status, body);
  }
  return r.json();
}

const net = (p: Promise<Response>) => p.catch(() => { throw new ApiError("Network error", "network"); });

export const api = {
  health: () => net(fetch("/api/health")).then((r) => json<Health>(r)),
  stats: () => net(fetch("/api/stats")).then((r) => json<Stats>(r)),
  scans: (q = "", verdict = "") =>
    net(fetch(`/api/scans?${new URLSearchParams({ q, verdict })}`)).then((r) => json<ScanSummary[]>(r)),
  scan: (id: string) => net(fetch(`/api/scans/${encodeURIComponent(id)}`)).then((r) => json<Report>(r)),
  remove: (id: string) => net(fetch(`/api/scans/${encodeURIComponent(id)}`, { method: "DELETE" })).then((r) => json(r)),
  samples: () => net(fetch("/api/demo/samples")).then((r) => json<Sample[]>(r)),
  analyzeSample: (id: string) => net(fetch(`/api/demo/samples/${id}/analyze`, { method: "POST" })).then((r) => json<Report>(r)),
  /** PDF report in the given UI language. */
  pdfUrl: (id: string, lang: Lang, inline = false) =>
    `/api/scans/${encodeURIComponent(id)}/report.pdf?${new URLSearchParams({ lang, ...(inline ? { inline: "true" } : {}) })}`,

  /** Upload with real progress events via XHR. */
  analyze(file: File, onProgress: (pct: number) => void): Promise<Report> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const fd = new FormData();
      fd.append("file", file);
      xhr.open("POST", "/api/analyze");
      xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(Math.round((e.loaded / e.total) * 100));
      xhr.onload = () => {
        let body: any = null;
        try { body = JSON.parse(xhr.responseText); } catch { /* ignore */ }
        if (xhr.status >= 200 && xhr.status < 300) resolve(body);
        else reject(toError(xhr.status, body));
      };
      xhr.onerror = () => reject(new ApiError("Network error", "network"));
      xhr.send(fd);
    });
  },
};
