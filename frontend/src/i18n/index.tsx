/**
 * Detective AI i18n: one dictionary per language in src/locales/*.json (shared with the backend, which
 * renders PDF reports and emits analysis findings as {key, params} messages from the same files).
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import az from "../locales/az.json";
import en from "../locales/en.json";
import ru from "../locales/ru.json";

export type Lang = "en" | "ru" | "az";
export const LANGS: Lang[] = ["en", "ru", "az"];
export const APP_NAME = "Detective AI";
const STORAGE_KEY = "detective-ai.lang";
const LOCALE: Record<Lang, string> = { en: "en-GB", ru: "ru-RU", az: "az-Latn-AZ" };

type Dict = { [k: string]: string | Dict };
const CATALOGS: Record<Lang, Dict> = { en: en as Dict, ru: ru as Dict, az: az as Dict };

/** A translatable message as emitted by the backend. */
export interface Msg { key: string; params?: Record<string, unknown> }
export type Params = Record<string, unknown>;

function lookup(dict: Dict, key: string): string | undefined {
  let cur: string | Dict | undefined = dict;
  for (const part of key.split(".")) {
    if (cur == null || typeof cur === "string") return undefined;
    cur = cur[part];
  }
  return typeof cur === "string" ? cur : undefined;
}

const isMsg = (v: unknown): v is Msg => typeof v === "object" && v !== null && "key" in (v as object);

function renderValue(lang: Lang, v: unknown): string {
  if (v == null) return "";
  if (Array.isArray(v)) return v.map((x) => renderValue(lang, x)).join("; ");
  if (isMsg(v)) return format(lang, v.key, v.params);
  return String(v);
}

/** Translate `key` with `{name}` placeholders; falls back to English, then to the key itself. */
export function format(lang: Lang, key: string, params?: Params): string {
  const template = lookup(CATALOGS[lang], key) ?? lookup(CATALOGS.en, key) ?? key;
  const all: Params = { app: APP_NAME, ...(params ?? {}) };
  return template.replace(/\{(\w+)\}/g, (m, name: string) => (name in all ? renderValue(lang, all[name]) : m));
}

function readStoredLang(): Lang {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return v === "ru" || v === "az" || v === "en" ? v : "en";
  } catch {
    return "en";
  }
}

interface I18n {
  lang: Lang;
  setLang: (l: Lang) => void;
  /** Static UI text. */
  t: (key: string, params?: Params) => string;
  /** Backend message (or list of messages); `fallback` is the stored English text for older scans. */
  tm: (msg: Msg | Msg[] | string | null | undefined, fallback?: string | null) => string;
  /** Translate a key if it exists, otherwise return `fallback` (e.g. raw ids from old data). */
  tk: (key: string, fallback: string) => string;
  fmtDate: (iso: string) => string;
  fmtNum: (n: number, digits?: number) => string;
}

const Ctx = createContext<I18n | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(readStoredLang);
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try { localStorage.setItem(STORAGE_KEY, l); } catch { /* storage unavailable: keep in memory only */ }
  }, []);
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);

  const value = useMemo<I18n>(() => ({
    lang,
    setLang,
    t: (key, params) => format(lang, key, params),
    tm: (msg, fallback) => {
      if (msg == null || (Array.isArray(msg) && msg.length === 0)) return fallback ?? "";
      if (typeof msg === "string") return msg;
      return renderValue(lang, msg);
    },
    tk: (key, fallback) => lookup(CATALOGS[lang], key) ?? lookup(CATALOGS.en, key) ?? fallback,
    fmtDate: (iso) => new Date(iso).toLocaleString(LOCALE[lang]),
    fmtNum: (n, digits = 2) => n.toLocaleString(LOCALE[lang], { minimumFractionDigits: digits, maximumFractionDigits: digits }),
  }), [lang, setLang]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n(): I18n {
  const v = useContext(Ctx);
  if (!v) throw new Error("useI18n must be used inside <I18nProvider>");
  return v;
}

/** Renders `**bold**` segments of a translated string as <b>. */
export function Rich({ text, boldClass = "text-slate-200" }: { text: string; boldClass?: string }) {
  const parts = text.split(/\*\*(.+?)\*\*/g);
  return <>{parts.map((p, i) => (i % 2 ? <b key={i} className={boldClass}>{p}</b> : <span key={i}>{p}</span>))}</>;
}

/** Errors thrown by the API client carry a stable code that maps to errors.<code>. */
export class ApiError extends Error {
  constructor(message: string, public code?: string, public params?: Params, public status?: number) {
    super(message);
  }
}

export function errorText(t: I18n["t"], e: unknown): string {
  if (e instanceof ApiError && e.code) return t(`errors.${e.code}`, { ...(e.params ?? {}), status: e.status });
  return e instanceof Error ? e.message : String(e);
}
