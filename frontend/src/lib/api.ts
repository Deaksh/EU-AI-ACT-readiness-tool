const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8060";

export type Option = { value: string; label: string };

export type Question = {
  id: string;
  section: number;
  section_title: string;
  order: number;
  text: string;
  type: "single" | "multi";
  options: Option[];
  show_if: { question_id: string; values: string[] } | null;
};

export type AssessPayload = Record<string, string | string[]>;

export type AssessBody = {
  answers: AssessPayload;
  email?: string | null;
  consent: boolean;
  contact_name?: string | null;
  company?: string | null;
  client_referrer?: string | null;
  page_url?: string | null;
  utm_source?: string | null;
  utm_medium?: string | null;
  utm_campaign?: string | null;
};

export type AssessResult = {
  score_points: number;
  score_percent: number;
  band: "green" | "yellow" | "orange" | "red";
  band_label: string;
  band_summary: string;
  critical_gaps: string[];
  risk_line: string;
  days_remaining: number;
  deadline: string;
  estimated_hours: number;
  next_steps: string[];
  calendly_url: string;
  website_url: string;
  waitlist_url: string;
  submission_id: number;
  email_delivery: "none" | "sent" | "failed" | "misconfigured";
};

export async function fetchQuestions(): Promise<Question[]> {
  const r = await fetch(`${API_BASE}/api/questions`, { cache: "no-store" });
  if (!r.ok) throw new Error("Failed to load questions");
  return r.json();
}

export async function submitAssessment(body: AssessBody): Promise<AssessResult> {
  const r = await fetch(`${API_BASE}/api/assess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      answers: body.answers,
      email: body.email?.trim() || null,
      consent: body.consent,
      contact_name: body.contact_name?.trim() || null,
      company: body.company?.trim() || null,
      client_referrer: body.client_referrer?.trim() || null,
      page_url: body.page_url?.trim() || null,
      utm_source: body.utm_source?.trim() || null,
      utm_medium: body.utm_medium?.trim() || null,
      utm_campaign: body.utm_campaign?.trim() || null,
    }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({})) as {
      detail?: string | { missing?: string[] } | Array<{ msg?: string }>;
    };
    const detail = err.detail;
    if (typeof detail === "object" && detail && "missing" in detail && detail.missing?.length) {
      throw new Error(`Please complete: ${detail.missing.join(", ")}`);
    }
    if (Array.isArray(detail) && detail[0]?.msg) {
      throw new Error(detail.map((d) => d.msg).filter(Boolean).join(" ") || "Invalid input.");
    }
    throw new Error(
      typeof detail === "string"
        ? detail
        : "Could not score assessment. Check all required fields."
    );
  }
  return r.json();
}

const ADMIN_TOKEN_KEY = "eu_ai_act_admin_token";

export function getAdminToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(ADMIN_TOKEN_KEY);
}

export function setAdminToken(token: string) {
  sessionStorage.setItem(ADMIN_TOKEN_KEY, token);
}

export function clearAdminToken() {
  sessionStorage.removeItem(ADMIN_TOKEN_KEY);
}

function adminAuthHeaders(): HeadersInit {
  const t = getAdminToken();
  const h: Record<string, string> = {};
  if (t) h.Authorization = `Bearer ${t}`;
  return h;
}

export type AdminSummary = {
  total: number;
  with_email: number;
  without_email: number;
  by_band: Record<string, number>;
  submissions: Array<{
    id: number;
    created_at: string | null;
    email: string | null;
    has_email: boolean;
    score_percent: number | string;
    band: string;
  }>;
};

export type AdminSubmission = {
  id: number;
  email: string | null;
  consent: boolean;
  created_at: string | null;
  meta: Record<string, unknown>;
  answers: Record<string, unknown>;
  report: Record<string, unknown>;
};

export async function adminLogin(email: string, password: string): Promise<void> {
  const r = await fetch(`${API_BASE}/api/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) {
    const err = (await r.json().catch(() => ({}))) as { detail?: unknown };
    const d = err.detail;
    let msg = "Sign-in failed.";
    if (typeof d === "string") {
      msg = d;
    } else if (Array.isArray(d) && d[0] && typeof d[0] === "object" && d[0] !== null && "msg" in d[0]) {
      msg = String((d[0] as { msg: string }).msg);
    } else if (r.status === 503) {
      msg = "Admin login is not configured on the API server.";
    } else if (r.status === 401) {
      msg = "Invalid email or password.";
    }
    throw new Error(msg);
  }
  const j = (await r.json()) as { access_token: string };
  setAdminToken(j.access_token);
}

export async function fetchAdminSummary(): Promise<AdminSummary> {
  const r = await fetch(`${API_BASE}/api/admin/summary`, {
    headers: { ...adminAuthHeaders() },
    cache: "no-store",
  });
  if (r.status === 404) {
    clearAdminToken();
    throw new Error("Not authorized or session expired.");
  }
  if (!r.ok) throw new Error("Could not load summary.");
  return r.json();
}

export async function fetchAdminSubmissions(
  limit = 50,
  offset = 0
): Promise<AdminSubmission[]> {
  const q = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  const r = await fetch(`${API_BASE}/api/admin/submissions?${q}`, {
    headers: { ...adminAuthHeaders() },
    cache: "no-store",
  });
  if (r.status === 404) {
    clearAdminToken();
    throw new Error("Not authorized or session expired.");
  }
  if (!r.ok) throw new Error("Could not load submissions.");
  return r.json();
}

export async function adminExportCsvBlob(): Promise<Blob> {
  const r = await fetch(`${API_BASE}/api/admin/submissions/export`, {
    headers: { ...adminAuthHeaders() },
  });
  if (r.status === 404) {
    clearAdminToken();
    throw new Error("Not authorized or session expired.");
  }
  if (!r.ok) throw new Error("Export failed.");
  return r.blob();
}
