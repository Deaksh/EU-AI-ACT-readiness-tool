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
};

export async function fetchQuestions(): Promise<Question[]> {
  const r = await fetch(`${API_BASE}/api/questions`, { cache: "no-store" });
  if (!r.ok) throw new Error("Failed to load questions");
  return r.json();
}

export async function submitAssessment(
  answers: AssessPayload
): Promise<AssessResult> {
  const r = await fetch(`${API_BASE}/api/assess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({})) as {
      detail?: string | { missing?: string[] };
    };
    const detail = err.detail;
    if (typeof detail === "object" && detail?.missing?.length) {
      throw new Error(`Please complete: ${detail.missing.join(", ")}`);
    }
    throw new Error(
      typeof detail === "string"
        ? detail
        : "Could not score assessment. Check all required fields."
    );
  }
  return r.json();
}
