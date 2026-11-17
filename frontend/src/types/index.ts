import type { Msg } from "../i18n";

export type Verdict = "ai_likely" | "ai_edited" | "authentic_likely" | "not_ai" | "manipulated_possible" | "inconclusive";
export type Decision = "ai" | "real" | "uncertain" | "unreliable";
export type ConfidenceLevel = "high" | "moderate" | "limited" | "conflict" | "none";
export interface FamilyMember { key: string; name: string; model: string; decision: Decision; score: number; score_kind: "raw" | "vendor_calibrated"; threshold?: string }
export interface DetectorFamily { family: string; name: string; vote: "ai" | "real" | "uncertain"; split: boolean; members: FamilyMember[] }
export interface ImageQuality { long_side: number; jpeg_quality: number | null; low_quality: boolean; reasons: ("small" | "compressed")[]; min_long_side: number; max_jpeg_quality: number }
/** Backend text: a message (or list of messages) for i18n; the plain-English field sits next to it. */
export type MsgLike = Msg | Msg[] | null | undefined;

export interface Evidence { strength: "strong" | "moderate" | "weak"; source: string; text: string; msg?: Msg }

export interface DetectorResult {
  key: string; model: string; architecture: string; license: string; role?: string;
  status: "ok" | "unavailable" | "error"; error?: string; device?: string;
  positive_score?: number; raw_outputs?: Record<string, number>; inference_ms?: number;
  full_image_score?: number; view_scores?: Record<string, number>; stability?: number; stable?: boolean;
  name?: string; family?: string; decision?: Decision; score_kind?: "raw" | "vendor_calibrated"; threshold?: string; input?: string; raw_logit?: number;
}

export interface Face {
  id: number; box: [number, number, number, number]; detection_confidence: number | null;
  manipulation_score: number | null; manipulation_raw?: Record<string, number>; flagged: boolean; note?: string; note_key?: string;
}

export interface Report {
  scan_id: string; filename: string; created_at: string; is_demo: boolean; processing_ms: number;
  file: { format: string; mime: string; width: number; height: number; mode: string; size_bytes: number; sha256: string; animated: boolean };
  detectors: DetectorResult[];
  metadata: {
    exif: Record<string, string>; exif_present: boolean; camera: { make?: string; model?: string; lens?: string } | null;
    capture_settings_present: boolean; software: string | null; editing_software_detected: string[];
    edit_history_in_xmp: boolean; xmp_present: boolean; png_text_chunks: Record<string, string>;
    ai_generation_markers: string[]; ai_generation_marker_msgs?: Msg[];
    c2pa: { present: boolean; validated: boolean; reader: string | null; summary: Record<string, unknown> | null };
    exiftool: Record<string, unknown> | null;
  };
  signal: {
    jpeg: { tables: number; estimated_quality: number } | null;
    ela: { mean_error: number; p99_error: number; block_nonuniformity: number; resave_quality: number };
    stats: { mean_rgb: number[]; std_rgb: number[]; sharpness_laplacian_var: number; noise_residual_std: number; unique_colors_sampled: number };
  };
  faces: { status: string; detector: string | null; manipulation_classifier?: string | null; manipulation_classifier_status?: string; face_count?: number; faces: Face[] };
  saliency: { status: string; method?: string; reason?: string; max_delta?: number; meaningful?: boolean };
  assessment: {
    verdict: Verdict; verdict_label: string; ai_likelihood: number | null; ai_likelihood_band: string | null;
    evidence_strength: string; detectors_available: number; detectors_total: number;
    detectors_disagree: boolean; detector_agreement?: string; unstable_reason?: string | null; low_resolution?: boolean;
    ai_votes?: number; not_ai_votes?: number;
    detection_confidence?: { level: ConfidenceLevel; direction: "ai" | "real" | null; agreeing: number; families: number };
    detector_families?: DetectorFamily[]; family_conflict?: boolean; family_split?: boolean; image_quality?: ImageQuality;
    evidence_for_ai: Evidence[]; evidence_against_ai: Evidence[]; manipulation_indicators: Evidence[];
    rules_fired: string[]; rules_msgs?: Msg[]; limitations: string[]; limitations_msgs?: Msg[];
    recommendations: string[]; recommendations_msgs?: Msg[]; method: string; method_msg?: Msg;
  };
  timeline?: Timeline;
  signals?: Signal[];
  visuals: Partial<Record<"original" | "saliency" | "ela" | "faces", string>>;
  stages: { stage: string; ms: number }[];
}

export interface TimelineEvent {
  time: string; source: string; source_key?: string; field: string; field_msg?: Msg; meaning: string; meaning_msg?: Msg;
  kind: "capture" | "create" | "modify" | "edit" | "scan"; timezone: string; tz?: "stated" | "local" | "utc";
}
export interface TimelineCheck {
  id: string; status: "ok" | "info" | "notice" | "warning";
  title: string; title_msg?: Msg; detail: string; detail_msg?: Msg; meaning: string; meaning_msg?: Msg;
}
export interface Timeline {
  events: TimelineEvent[]; edit_history: { action: string; when: string | null; software: string | null }[];
  software: string | null; creator_tool: string | null; timezone_offsets: Record<string, string>; checks: TimelineCheck[]; embedded_count: number;
}
export interface Signal {
  id: string; group: string; group_key?: string; name: string; name_msg?: Msg;
  status: "points_ai" | "points_camera" | "points_edit" | "neutral" | "unreliable" | "unavailable";
  value: string | null; value_msg?: MsgLike; finding: string; finding_msg?: MsgLike; meaning: string; meaning_msg?: Msg; strength: string;
}

export interface ScanSummary {
  scan_id: string; filename: string; created_at: string; verdict: Verdict; verdict_label: string;
  ai_likelihood: number | null; file_type: string; width: number; height: number; is_demo: boolean;
  evidence_strength: string; thumbnail: string; detection_confidence?: ConfidenceLevel | null;
}

export interface Stats { total: number; ai_likely: number; ai_edited?: number; authentic_likely: number; not_ai: number; manipulated_possible: number; inconclusive: number; recent: ScanSummary[] }

export interface Health {
  status: "ready" | "degraded"; backend: boolean; database: boolean; models_loaded: boolean; detector_ready: boolean;
  models: { key: string; model: string; license: string; available: boolean; device: string | null; error: string | null }[];
  face_detector: string | null; dependencies: Record<string, boolean>; gpu: string | null; python: string; offline_mode: boolean; max_upload_mb: number;
}

export interface Sample { id: string; file: string; title: string; category: string; provenance: string; license: string; source_url?: string; notes?: string; thumbnail: string }
