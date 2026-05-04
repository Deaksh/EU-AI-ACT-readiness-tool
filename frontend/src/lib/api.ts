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
