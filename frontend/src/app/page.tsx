"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  type AssessResult,
  type Question,
  fetchQuestions,
  submitAssessment,
} from "@/lib/api";
import { AdminModal } from "@/components/AdminModal";
import { bandStyles, bandShortLabel, type ReportBand } from "@/lib/bandTheme";

type Answers = Record<string, string | string[]>;

const BEACON_SITE = "https://beacon-bio.carrd.co";

function LandingScreen({
  onStart,
  onAdmin,
}: {
  onStart: () => void;
  onAdmin: () => void;
}) {
  return (
    <div className="min-h-screen bg-[radial-gradient(1000px_520px_at_50%_-5%,#e0e7ff_0%,transparent_55%),radial-gradient(800px_480px_at_100%_30%,#ccfbf1_0%,transparent_50%),var(--background)] dark:bg-[radial-gradient(1000px_520px_at_50%_-5%,#1e1b4b_0%,transparent_55%),radial-gradient(800px_480px_at_100%_30%,#134e4a_0%,transparent_50%),var(--background)]">
      <header className="border-b border-black/5 bg-white/80 backdrop-blur-md dark:border-white/10 dark:bg-black/40">
        <div className="mx-auto flex max-w-3xl items-center justify-end px-4 py-4 sm:px-6">
          <button
            type="button"
            onClick={onAdmin}
            className="rounded-xl border border-black/10 bg-white/90 px-4 py-2 text-sm font-medium text-neutral-800 shadow-sm transition hover:bg-white dark:border-white/15 dark:bg-neutral-950/60 dark:text-neutral-100 dark:hover:bg-neutral-900"
          >
            Admin
          </button>
        </div>
      </header>

      <main className="mx-auto flex max-w-3xl flex-col items-center px-4 py-16 sm:px-6 sm:py-24">
        <div className="w-full max-w-lg text-center sm:text-left">
          <p className="text-sm font-semibold tracking-[0.28em] text-indigo-900/80 dark:text-indigo-200/90">
            BEACON
          </p>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-50 sm:text-4xl">
            IND Readiness Assessment
          </h1>
          <p className="mt-4 text-base leading-relaxed text-neutral-600 dark:text-neutral-300">
            A concise, IND-focused questionnaire covering analytical data, CMC documentation, and
            regulatory strategy. Estimated time: about two minutes.
          </p>
          <p className="mt-3">
            <a
              href={BEACON_SITE}
              target="_blank"
              rel="noreferrer"
              className="text-sm font-medium text-teal-700 underline-offset-4 hover:underline dark:text-teal-400"
            >
              beacon-bio.carrd.co
            </a>
          </p>

          <ol className="mt-10 space-y-5 text-left">
            {[
              "Analytical data — methods, data integrity, and audit readiness.",
              "CMC documentation — M4Q narratives, version control, and eCTD alignment.",
              "Regulatory strategy — mapping, resourcing, timelines, and risk mitigation.",
            ].map((text, i) => (
              <li key={text} className="flex gap-4">
                <span
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-indigo-200 bg-indigo-50 text-sm font-semibold text-indigo-900 dark:border-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-100"
                  aria-hidden
                >
                  {i + 1}
                </span>
                <span className="pt-1 text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
                  {text}
                </span>
              </li>
            ))}
          </ol>

          <div className="mt-10 flex flex-col items-center gap-4 sm:items-start">
            <button
              type="button"
              onClick={onStart}
              className="inline-flex h-12 items-center justify-center rounded-xl bg-indigo-900 px-8 text-sm font-semibold text-white shadow-md transition hover:bg-indigo-800 dark:bg-indigo-600 dark:hover:bg-indigo-500"
            >
              Start assessment
            </button>
            <a
              href={BEACON_SITE}
              target="_blank"
              rel="noreferrer"
              className="text-sm font-medium text-teal-700 underline-offset-4 hover:underline dark:text-teal-400"
            >
              beacon-bio.carrd.co
            </a>
          </div>

          <p className="mt-12 text-center text-xs leading-relaxed text-neutral-500 dark:text-neutral-400 sm:text-left">
            For educational planning purposes only — not legal or regulatory advice.
          </p>
        </div>
      </main>
    </div>
  );
}

function visible(q: Question, answers: Answers): boolean {
  if (!q.show_if) return true;
  const v = answers[q.show_if.question_id];
  if (typeof v !== "string") return false;
  return q.show_if.values.includes(v);
}

function sectionBadge(n: number): string {
  const names = [
    "",
    "AI inventory",
    "Classification",
    "Compliance obligations",
    "Governance",
  ];
  return names[n] ?? `Section ${n}`;
}

export default function Home() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Answers>({});
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [result, setResult] = useState<AssessResult | null>(null);
  const [email, setEmail] = useState("");
  const [contactName, setContactName] = useState("");
  const [company, setCompany] = useState("");
  const [consent, setConsent] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  const [assessmentStarted, setAssessmentStarted] = useState(false);

  useEffect(() => {
    fetchQuestions()
      .then(setQuestions)
      .catch(() => setLoadError("Unable to load questionnaire. Is the API running?"));
  }, []);

  const grouped = useMemo(() => {
    const map = new Map<number, Question[]>();
    for (const q of questions) {
      const list = map.get(q.section) ?? [];
      list.push(q);
      map.set(q.section, list);
    }
    return map;
  }, [questions]);

  const answeredCount = useMemo(() => {
    let n = 0;
    for (const q of questions) {
      if (!visible(q, answers)) continue;
      if (q.id === "q8" && answers["q7"] === "no") {
        n++;
        continue;
      }
      const v = answers[q.id];
      if (q.type === "multi" && Array.isArray(v) && v.length > 0) n++;
      if (q.type === "single" && typeof v === "string" && v) n++;
    }
    return n;
  }, [questions, answers]);

  const setSingle = (id: string, value: string) => {
    setAnswers((prev) => {
      const next = { ...prev, [id]: value };
      if (id === "q7" && value === "no") {
        delete next["q8"];
      }
      return next;
    });
  };

  const toggleMulti = (id: string, value: string) => {
    setAnswers((prev) => {
      const cur = (prev[id] as string[] | undefined) ?? [];
      const has = cur.includes(value);
      const nextList = has ? cur.filter((x) => x !== value) : [...cur, value];
      return { ...prev, [id]: nextList };
    });
  };

  const onSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setFormError(null);
      setSubmitting(true);
      try {
        const payload: Answers = { ...answers };
        for (const q of questions) {
          if (!visible(q, payload) && q.id === "q8") {
            delete payload["q8"];
          }
        }
        if (!consent) {
          setFormError(
            "Please confirm you agree to store your responses (and receive email if you added an address)."
          );
          setSubmitting(false);
          return;
        }
        const sp =
          typeof window !== "undefined"
            ? new URLSearchParams(window.location.search)
            : null;
        const res = await submitAssessment({
          answers: payload,
          email: email.trim() || null,
          consent,
          contact_name: contactName.trim() || null,
          company: company.trim() || null,
          client_referrer:
            typeof document !== "undefined" && document.referrer
              ? document.referrer
              : null,
          page_url: typeof window !== "undefined" ? window.location.href : null,
          utm_source: sp?.get("utm_source") || null,
          utm_medium: sp?.get("utm_medium") || null,
          utm_campaign: sp?.get("utm_campaign") || null,
        });
        setResult(res);
        setTimeout(() => {
          document.getElementById("results")?.scrollIntoView({ behavior: "smooth" });
        }, 100);
      } catch (err) {
        setFormError(
          err instanceof Error ? err.message : "Something went wrong. Try again."
        );
      } finally {
        setSubmitting(false);
      }
    },
    [answers, questions, consent, email, contactName, company]
  );

  const reset = () => {
    setAnswers({});
    setResult(null);
    setFormError(null);
    setEmail("");
    setContactName("");
    setCompany("");
    setConsent(false);
    setAssessmentStarted(false);
  };

  const startAssessment = () => {
    setAssessmentStarted(true);
    setTimeout(() => {
      document.getElementById("questionnaire")?.scrollIntoView({ behavior: "smooth" });
    }, 50);
  };

  if (loadError) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="max-w-md rounded-2xl border border-rose-200/60 bg-rose-50/50 p-6 text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/20 dark:text-rose-200">
          <p className="font-medium">{loadError}</p>
          <p className="mt-2 text-sm text-rose-700/80 dark:text-rose-300/80">
            Restart the API after updating (CORS now allows any localhost port).
            Start:{" "}
            <code className="rounded bg-rose-100/80 px-1.5 py-0.5 text-xs dark:bg-rose-900/40">
              cd backend &amp;&amp; uvicorn app.main:app --reload --port 8060
            </code>
          </p>
        </div>
      </div>
    );
  }

  if (!questions.length) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-700 dark:border-neutral-600 dark:border-t-neutral-200" />
      </div>
    );
  }

  if (!assessmentStarted) {
    return (
      <>
        <LandingScreen onStart={startAssessment} onAdmin={() => setAdminOpen(true)} />
        <AdminModal open={adminOpen} onClose={() => setAdminOpen(false)} />
      </>
    );
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(1000px_520px_at_50%_-5%,#e0e7ff_0%,transparent_55%),radial-gradient(800px_480px_at_100%_20%,#ccfbf1_0%,transparent_45%),var(--background)] dark:bg-[radial-gradient(1000px_520px_at_50%_-5%,#1e1b4b_0%,transparent_55%),radial-gradient(800px_480px_at_100%_20%,#134e4a_0%,transparent_45%),var(--background)]">
      <header className="border-b border-black/5 bg-white/70 backdrop-blur-md dark:border-white/10 dark:bg-black/30">
        <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 flex-1 space-y-2">
              <p className="text-xs font-semibold tracking-[0.2em] text-indigo-900/70 dark:text-indigo-200/80">
                BEACON
              </p>
              <h1 className="text-2xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-50 sm:text-3xl">
                IND Readiness Assessment
              </h1>
              <p className="max-w-2xl text-sm leading-relaxed text-neutral-600 dark:text-neutral-300">
                High-level self-assessment across analytical, CMC, and regulatory themes. Results
                are indicative only — confirm with your quality and regulatory leads.
              </p>
              <div className="flex flex-wrap items-center gap-2 pt-1">
                {!result ? (
                  <button
                    type="button"
                    onClick={() => setAssessmentStarted(false)}
                    className="text-xs font-medium text-teal-700 underline-offset-4 hover:underline dark:text-teal-400"
                  >
                    ← Back to overview
                  </button>
                ) : null}
                <span className="rounded-full border border-black/5 bg-white/60 px-2.5 py-1 text-xs text-neutral-500 dark:border-white/10 dark:bg-white/5 dark:text-neutral-400">
                  {answeredCount} / 20 answered
                </span>
                <span className="rounded-full border border-black/5 bg-white/60 px-2.5 py-1 text-xs text-neutral-500 dark:border-white/10 dark:bg-white/5 dark:text-neutral-400">
                  ~2 min
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setAdminOpen(true)}
              className="shrink-0 rounded-xl border border-black/10 bg-white/90 px-4 py-2 text-sm font-medium text-neutral-800 shadow-sm transition hover:bg-white dark:border-white/15 dark:bg-neutral-950/60 dark:text-neutral-100 dark:hover:bg-neutral-900"
            >
              Admin
            </button>
          </div>
        </div>
      </header>

      <main id="questionnaire" className="mx-auto max-w-3xl scroll-mt-20 px-4 py-8 sm:px-6">
        <form onSubmit={onSubmit} className="space-y-10">
          {Array.from(grouped.entries())
            .sort((a, b) => a[0] - b[0])
            .map(([sectionNum, qs]) => (
              <section
                key={sectionNum}
                className="rounded-2xl border border-black/5 bg-white/80 p-5 shadow-sm dark:border-white/10 dark:bg-neutral-950/50 sm:p-7"
              >
                <div className="mb-5 flex items-baseline justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                      Section {sectionNum}: {sectionBadge(sectionNum)}
                    </h2>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400">
                      {qs.filter((q) => visible(q, answers)).length} questions
                      in this section
                    </p>
                  </div>
                </div>

                <div className="space-y-8">
                  {qs.map((q) => {
                    if (!visible(q, answers)) return null;
                    if (q.id === "q8" && answers["q7"] === "no") return null;

                    return (
                      <fieldset key={q.id} className="space-y-3">
                        <legend className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                          <span className="mr-2 text-neutral-400 dark:text-neutral-500">
                            {q.order}.
                          </span>
                          {q.text}
                        </legend>

                        {q.type === "single" ? (
                          <div className="grid gap-2 sm:grid-cols-3">
                            {q.options.map((o) => {
                              const active = answers[q.id] === o.value;
                              return (
                                <label
                                  key={o.value}
                                  className={[
                                    "flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2.5 text-sm transition",
                                    active
                                      ? "border-sky-500/70 bg-sky-50/90 text-sky-950 dark:border-sky-400/60 dark:bg-sky-950/40 dark:text-sky-50"
                                      : "border-black/5 bg-white/40 hover:border-black/10 dark:border-white/10 dark:bg-white/5 dark:hover:border-white/20",
                                  ].join(" ")}
                                >
                                  <input
                                    type="radio"
                                    name={q.id}
                                    value={o.value}
                                    className="sr-only"
                                    checked={active}
                                    onChange={() => setSingle(q.id, o.value)}
                                  />
                                  <span
                                    className={[
                                      "h-2 w-2 shrink-0 rounded-full",
                                      active ? "bg-sky-600 dark:bg-sky-400" : "bg-neutral-300 dark:bg-neutral-600",
                                    ].join(" ")}
                                  />
                                  {o.label}
                                </label>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="grid gap-2 sm:grid-cols-2">
                            {q.options.map((o) => {
                              const selected = (
                                (answers[q.id] as string[] | undefined) ?? []
                              ).includes(o.value);
                              return (
                                <label
                                  key={o.value}
                                  className={[
                                    "flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-sm transition",
                                    selected
                                      ? "border-violet-500/70 bg-violet-50/90 text-violet-950 dark:border-violet-400/60 dark:bg-violet-950/40 dark:text-violet-50"
                                      : "border-black/5 bg-white/40 hover:border-black/10 dark:border-white/10 dark:bg-white/5 dark:hover:border-white/20",
                                  ].join(" ")}
                                >
                                  <input
                                    type="checkbox"
                                    className="sr-only"
                                    checked={selected}
                                    onChange={() => toggleMulti(q.id, o.value)}
                                  />
                                  <span
                                    className={[
                                      "flex h-4 w-4 shrink-0 items-center justify-center rounded border text-[10px]",
                                      selected
                                        ? "border-violet-600 bg-violet-600 text-white dark:border-violet-400 dark:bg-violet-500"
                                        : "border-neutral-300 bg-white dark:border-neutral-600 dark:bg-neutral-900",
                                    ].join(" ")}
                                  >
                                    {selected ? "✓" : ""}
                                  </span>
                                  {o.label}
                                </label>
                              );
                            })}
                          </div>
                        )}
                      </fieldset>
                    );
                  })}
                </div>
              </section>
            ))}

          {formError ? (
            <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-200">
              {formError}
            </p>
          ) : null}

          <div className="rounded-2xl border border-black/5 bg-white/80 p-5 dark:border-white/10 dark:bg-neutral-950/50 sm:p-6">
            <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
              Contact (optional)
            </p>
            <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
              Helps us follow up. Email can stay blank if you only want the on-screen report.
            </p>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div>
                <label className="text-xs text-neutral-600 dark:text-neutral-400" htmlFor="contact-name">
                  Name
                </label>
                <input
                  id="contact-name"
                  type="text"
                  name="contact_name"
                  autoComplete="name"
                  value={contactName}
                  onChange={(e) => setContactName(e.target.value)}
                  placeholder="Alex Doe"
                  className="mt-1 w-full rounded-xl border border-black/10 bg-white px-3 py-2.5 text-sm text-neutral-900 outline-none ring-sky-500/30 placeholder:text-neutral-400 focus:ring-2 dark:border-white/10 dark:bg-neutral-900 dark:text-neutral-100"
                />
              </div>
              <div>
                <label className="text-xs text-neutral-600 dark:text-neutral-400" htmlFor="company">
                  Organization
                </label>
                <input
                  id="company"
                  type="text"
                  name="company"
                  autoComplete="organization"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="Company or team"
                  className="mt-1 w-full rounded-xl border border-black/10 bg-white px-3 py-2.5 text-sm text-neutral-900 outline-none ring-sky-500/30 placeholder:text-neutral-400 focus:ring-2 dark:border-white/10 dark:bg-neutral-900 dark:text-neutral-100"
                />
              </div>
            </div>
            <label className="mt-4 block text-sm font-medium text-neutral-900 dark:text-neutral-100">
              Email (optional)
            </label>
            <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
              We&apos;ll send this personalized report to you. Leave blank to only see results on
              this page.
            </p>
            <input
              type="email"
              name="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="mt-3 w-full rounded-xl border border-black/10 bg-white px-3 py-2.5 text-sm text-neutral-900 outline-none ring-sky-500/30 placeholder:text-neutral-400 focus:ring-2 dark:border-white/10 dark:bg-neutral-900 dark:text-neutral-100"
            />
            <label className="mt-4 flex cursor-pointer items-start gap-3 text-sm text-neutral-700 dark:text-neutral-300">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-1 h-4 w-4 shrink-0 rounded border-neutral-300 text-sky-600 focus:ring-sky-500 dark:border-neutral-600"
              />
              <span>
                I agree that my questionnaire responses may be stored securely for internal review
                and follow-up. If I entered an email, I agree to receive my report at that address.
              </span>
            </label>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex h-11 items-center justify-center rounded-xl bg-neutral-900 px-6 text-sm font-medium text-white shadow-sm transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-white"
            >
              {submitting ? "Scoring…" : "Get instant score"}
            </button>
            <button
              type="button"
              onClick={reset}
              className="inline-flex h-11 items-center justify-center rounded-xl border border-black/10 bg-white/60 px-6 text-sm font-medium text-neutral-800 transition hover:bg-white dark:border-white/15 dark:bg-neutral-950/50 dark:text-neutral-100 dark:hover:bg-neutral-900"
            >
              Clear answers
            </button>
          </div>
        </form>

        {result ? (
          <section
            id="results"
            className="report-enter-delay-1 mt-12 space-y-6 scroll-mt-24 border-t border-black/5 pt-10 dark:border-white/10"
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-neutral-900 dark:bg-neutral-100" />
                <h2 className="text-xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-50">
                  Personalized report
                </h2>
              </div>
              {result.email_delivery === "sent" ? (
                <p className="text-sm text-emerald-700 dark:text-emerald-400">
                  A detailed copy was sent to your email.
                </p>
              ) : null}
              {result.email_delivery === "failed" ? (
                <p className="text-sm text-amber-800 dark:text-amber-300">
                  We couldn&apos;t send email — your report is still shown below. Try again later or
                  contact us.
                </p>
              ) : null}
              {result.email_delivery === "misconfigured" && email.trim() ? (
                <p className="text-sm text-amber-800 dark:text-amber-300">
                  Email delivery isn&apos;t configured on the server yet — your report appears
                  below.
                </p>
              ) : null}
            </div>

            <div
              className={`report-enter rounded-2xl border p-6 sm:p-8 ${bandStyles[result.band as ReportBand].card}`}
            >
              <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
                    Your IND readiness snapshot
                  </p>
                  <p className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-4xl font-semibold tabular-nums tracking-tight text-neutral-900 dark:text-neutral-50">
                    <span>{result.score_percent}%</span>
                    <span
                      className={[
                        "inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold uppercase tracking-wide",
                        result.band === "green"
                          ? "bg-emerald-600 text-white dark:bg-emerald-500"
                          : result.band === "yellow"
                            ? "bg-amber-500 text-neutral-900 dark:bg-amber-400"
                            : result.band === "orange"
                              ? "bg-orange-500 text-white dark:bg-orange-600"
                              : "bg-rose-600 text-white dark:bg-rose-500",
                      ].join(" ")}
                    >
                      {bandShortLabel(result.band_label)}
                    </span>
                  </p>
                  <p className="mt-3 max-w-prose text-sm leading-relaxed text-neutral-600 dark:text-neutral-300">
                    {result.band_summary}
                  </p>
                </div>
                <div className="w-full sm:max-w-xs">
                  <div className="h-2.5 overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
                    <div
                      className={`report-bar-fill h-full rounded-full bg-gradient-to-r ${bandStyles[result.band as ReportBand].bar}`}
                      style={{ width: `${Math.min(100, Math.max(0, result.score_percent))}%` }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
                    Model score: {result.score_points} / 20 weighted points
                  </p>
                </div>
              </div>
            </div>

            <div className="report-enter-delay-2 grid gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-black/5 bg-white/80 p-6 dark:border-white/10 dark:bg-neutral-950/50">
                <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
                  Critical gaps
                </h3>
                {result.critical_gaps.length ? (
                  <ul className="mt-3 space-y-2 text-sm text-neutral-700 dark:text-neutral-300">
                    {result.critical_gaps.map((g) => (
                      <li key={g} className="flex gap-2">
                        <span className="text-rose-500" aria-hidden>
                          ✕
                        </span>
                        <span>{g}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-sm text-neutral-600 dark:text-neutral-400">
                    No major gaps flagged on this pass — keep validating with your legal team.
                  </p>
                )}
              </div>

              <div className="rounded-2xl border border-black/5 bg-white/80 p-6 dark:border-white/10 dark:bg-neutral-950/50">
                <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
                  Risk snapshot
                </h3>
                <ul className="mt-3 space-y-2 text-sm text-neutral-700 dark:text-neutral-300">
                  <li className="flex gap-2">
                    <span
                      className={
                        bandStyles[result.band as ReportBand].dot +
                        " mt-1.5 h-2 w-2 shrink-0 rounded-full"
                      }
                    />
                    <span>{result.risk_line}</span>
                  </li>
                  <li className="flex gap-2 text-neutral-600 dark:text-neutral-400">
                    <span className="mt-0.5" aria-hidden>
                      ⏰
                    </span>
                    <span>
                      Time to key deadline ({result.deadline}):{" "}
                      <strong className="text-neutral-800 dark:text-neutral-200">
                        {result.days_remaining} days
                      </strong>
                    </span>
                  </li>
                  <li className="flex gap-2 text-neutral-600 dark:text-neutral-400">
                    <span className="mt-0.5" aria-hidden>
                      📊
                    </span>
                    <span>
                      Estimated remediation effort (indicative):{" "}
                      <strong className="text-neutral-800 dark:text-neutral-200">
                        {result.estimated_hours} hours
                      </strong>{" "}
                      to strengthen posture
                    </span>
                  </li>
                </ul>
              </div>
            </div>

            <div className="report-enter-delay-3 rounded-2xl border border-black/5 bg-white/80 p-6 dark:border-white/10 dark:bg-neutral-950/50">
              <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
                Recommended next steps
              </h3>
              <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm text-neutral-700 dark:text-neutral-300">
                {result.next_steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </div>

            <div className="report-enter-delay-4 rounded-2xl border border-dashed border-sky-300/60 bg-sky-50/50 p-6 dark:border-sky-800/50 dark:bg-sky-950/20">
              <h3 className="text-sm font-semibold text-sky-950 dark:text-sky-100">
                Need help?
              </h3>
              <div className="mt-3 flex flex-col gap-2 text-sm text-sky-900/90 dark:text-sky-200/90">
                <a
                  href={result.calendly_url}
                  className="font-medium underline-offset-4 hover:underline"
                  target="_blank"
                  rel="noreferrer"
                >
                  Schedule a free consultation (Calendly)
                </a>
                <a
                  href={result.website_url}
                  className="font-medium underline-offset-4 hover:underline"
                  target="_blank"
                  rel="noreferrer"
                >
                  Beacon Watchtower (website)
                </a>
                <a
                  href={result.waitlist_url}
                  className="font-medium underline-offset-4 hover:underline"
                  target="_blank"
                  rel="noreferrer"
                >
                  Get early access — join the waitlist
                </a>
              </div>
            </div>
          </section>
        ) : null}
      </main>

      <footer className="border-t border-black/5 py-10 text-center text-xs leading-relaxed text-neutral-500 dark:border-white/10 dark:text-neutral-500">
        <p>
          Readiness bands: 18–20 strong (green), 15–17 minor gaps (yellow), 12–14 significant gaps
          (orange), below 12 high risk (red). Weighted scoring — not a regulatory determination.
        </p>
        <p className="mt-3">
          For educational planning purposes only — not legal or regulatory advice.
        </p>
      </footer>

      <AdminModal open={adminOpen} onClose={() => setAdminOpen(false)} />
    </div>
  );
}
