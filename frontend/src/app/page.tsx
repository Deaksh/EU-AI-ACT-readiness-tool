"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  type AssessResult,
  type Question,
  type Regulation,
  type RegulationReport,
  fetchQuestions,
  fetchRegulations,
  submitAssessment,
} from "@/lib/api";
import { AdminModal } from "@/components/AdminModal";
import { bandStyles, bandShortLabel, type ReportBand } from "@/lib/bandTheme";

type Answers = Record<string, string | string[]>;
type Screen = "landing" | "reg-select" | "assessment";

const BEACON_PUBLIC_SITE = "https://www.beaconone.net/ai-compliance";

// ──────────────────────────────────────────────
// Landing
// ──────────────────────────────────────────────

function LandingScreen({ onStart, onAdmin }: { onStart: () => void; onAdmin: () => void }) {
  const pillars = [
    "AI inventory — systems, documentation, and EU user scope.",
    "Classification — risk categories, high-risk exposure, and prohibited practices.",
    "Compliance obligations — risk management, documentation, conformity.",
    "Governance — ownership, incidents, monitoring, and audit readiness.",
  ];

  return (
    <div className="min-h-screen bg-[radial-gradient(1200px_600px_at_50%_-10%,#dbeafe_0%,transparent_55%),radial-gradient(900px_500px_at_100%_20%,#fef3c7_0%,transparent_45%),var(--background)] dark:bg-[radial-gradient(1200px_600px_at_50%_-10%,#0c2649_0%,transparent_55%),radial-gradient(900px_500px_at_100%_20%,#3a2708_0%,transparent_45%),var(--background)]">
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
          <p className="text-xs font-medium uppercase tracking-widest text-sky-700/85 dark:text-sky-300/85">
            Free readiness snapshot
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-50 sm:text-4xl">
            AI Compliance Readiness Assessment
          </h1>
          <p className="mt-4 text-base leading-relaxed text-neutral-600 dark:text-neutral-300">
            A concise questionnaire covering EU AI Act, GDPR, and NIST AI RMF — built for a quick
            multi-regulation compliance posture check. Estimated time: about two to five minutes.
          </p>
          <p className="mt-3">
            <a
              href={BEACON_PUBLIC_SITE}
              target="_blank"
              rel="noreferrer"
              className="text-sm font-medium text-sky-700 underline-offset-4 hover:underline dark:text-sky-400"
            >
              beaconone.net/ai-compliance
            </a>
          </p>

          <ol className="mt-10 space-y-5 text-left">
            {pillars.map((text, i) => (
              <li key={text} className="flex gap-4">
                <span
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-sky-200 bg-sky-50 text-sm font-semibold text-sky-900 dark:border-sky-800 dark:bg-sky-950/50 dark:text-sky-100"
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
              className="inline-flex h-12 items-center justify-center rounded-xl bg-neutral-900 px-8 text-sm font-semibold text-white shadow-md transition hover:bg-neutral-800 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-white"
            >
              Start assessment
            </button>
            <a
              href={BEACON_PUBLIC_SITE}
              target="_blank"
              rel="noreferrer"
              className="text-sm font-medium text-sky-700 underline-offset-4 hover:underline dark:text-sky-400"
            >
              beaconone.net/ai-compliance
            </a>
          </div>

          <p className="mt-12 text-center text-xs leading-relaxed text-neutral-500 dark:text-neutral-400 sm:text-left">
            For educational planning purposes only — not legal advice. Consult qualified counsel for
            your systems and use cases.
          </p>
        </div>
      </main>
    </div>
  );
}

// ──────────────────────────────────────────────
// Regulation selector
// ──────────────────────────────────────────────

const JURISDICTION_COLORS: Record<string, string> = {
  EU: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800/60",
  US: "bg-red-50 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-800/60",
  International:
    "bg-violet-50 text-violet-700 border-violet-200 dark:bg-violet-950/40 dark:text-violet-300 dark:border-violet-800/60",
};

function RegulationSelectorScreen({
  onContinue,
  onBack,
}: {
  onContinue: (codes: string[]) => void;
  onBack: () => void;
}) {
  const [regulations, setRegulations] = useState<Regulation[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set(["eu_ai_act"]));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRegulations()
      .then((regs) => {
        setRegulations(regs);
        setLoading(false);
      })
      .catch(() => {
        setError("Unable to load regulations. Is the API running?");
        setLoading(false);
      });
  }, []);

  const toggle = (code: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(code)) {
        if (next.size > 1) next.delete(code);
      } else {
        next.add(code);
      }
      return next;
    });
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(1200px_600px_at_50%_-10%,#dbeafe_0%,transparent_55%),radial-gradient(900px_500px_at_100%_20%,#fef3c7_0%,transparent_45%),var(--background)] dark:bg-[radial-gradient(1200px_600px_at_50%_-10%,#0c2649_0%,transparent_55%),radial-gradient(900px_500px_at_100%_20%,#3a2708_0%,transparent_45%),var(--background)]">
      <header className="border-b border-black/5 bg-white/80 backdrop-blur-md dark:border-white/10 dark:bg-black/40">
        <div className="mx-auto flex max-w-3xl items-center gap-4 px-4 py-4 sm:px-6">
          <button
            type="button"
            onClick={onBack}
            className="text-sm font-medium text-sky-700 underline-offset-4 hover:underline dark:text-sky-400"
          >
            ← Back
          </button>
          <span className="text-sm text-neutral-500 dark:text-neutral-400">
            Step 1 of 2 — Select regulations
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-50">
            Which regulations apply to your organisation?
          </h1>
          <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-300">
            Select all that apply. EU AI Act is pre-selected. You must keep at least one selected.
          </p>
        </div>

        {error ? (
          <div className="rounded-2xl border border-rose-200/60 bg-rose-50/50 p-6 text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/20 dark:text-rose-200">
            {error}
          </div>
        ) : loading ? (
          <div className="flex justify-center py-16">
            <div className="h-10 w-10 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-700 dark:border-neutral-600 dark:border-t-neutral-200" />
          </div>
        ) : (
          <div className="space-y-4">
            {regulations.map((reg) => {
              const isSelected = selected.has(reg.code);
              const jColor =
                JURISDICTION_COLORS[reg.jurisdiction ?? ""] ||
                JURISDICTION_COLORS["International"];
              return (
                <button
                  key={reg.code}
                  type="button"
                  onClick={() => toggle(reg.code)}
                  className={[
                    "w-full rounded-2xl border p-5 text-left transition",
                    isSelected
                      ? "border-sky-500/70 bg-sky-50/90 shadow-sm dark:border-sky-400/60 dark:bg-sky-950/40"
                      : "border-black/5 bg-white/80 hover:border-black/15 dark:border-white/10 dark:bg-neutral-950/50 dark:hover:border-white/20",
                  ].join(" ")}
                >
                  <div className="flex items-start gap-3">
                    <span
                      className={[
                        "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border text-[10px] font-bold",
                        isSelected
                          ? "border-sky-600 bg-sky-600 text-white dark:border-sky-400 dark:bg-sky-500"
                          : "border-neutral-300 bg-white dark:border-neutral-600 dark:bg-neutral-900",
                      ].join(" ")}
                    >
                      {isSelected ? "✓" : ""}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
                          {reg.name}
                        </span>
                        {reg.jurisdiction ? (
                          <span
                            className={`rounded-full border px-2 py-0.5 text-xs font-medium ${jColor}`}
                          >
                            {reg.jurisdiction}
                          </span>
                        ) : null}
                        {reg.deadline ? (
                          <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-300">
                            Deadline {reg.deadline}
                          </span>
                        ) : null}
                      </div>
                      {reg.description ? (
                        <p className="mt-1.5 text-xs leading-relaxed text-neutral-600 dark:text-neutral-400">
                          {reg.description}
                        </p>
                      ) : null}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}

        <div className="mt-8 flex items-center gap-4">
          <button
            type="button"
            disabled={selected.size === 0 || loading}
            onClick={() => onContinue(Array.from(selected))}
            className="inline-flex h-11 items-center justify-center rounded-xl bg-neutral-900 px-6 text-sm font-semibold text-white shadow-sm transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-white"
          >
            Continue ({selected.size} selected)
          </button>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            {Array.from(selected).join(", ")}
          </p>
        </div>

        <p className="mt-8 text-xs text-neutral-500 dark:text-neutral-400">
          For educational planning only — not legal advice.
        </p>
      </main>
    </div>
  );
}

// ──────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────

function visible(q: Question, answers: Answers): boolean {
  if (!q.show_if) return true;
  const v = answers[q.show_if.question_id];
  if (typeof v !== "string") return false;
  return q.show_if.values.includes(v);
}

function sectionBadge(regCode: string, n: number, title: string): string {
  const regPrefix: Record<string, string> = {
    eu_ai_act: "EU AI Act",
    gdpr: "GDPR",
    nist_ai_rmf: "NIST AI RMF",
    iso_42001: "ISO 42001",
  };
  const prefix = regPrefix[regCode] ?? regCode.toUpperCase();
  return `${prefix} — ${title}`;
}

// A section key combines regulation_code + section number so sections across regs don't collide
function sectionKey(regCode: string, sectionNum: number): string {
  return `${regCode}::${sectionNum}`;
}

// ──────────────────────────────────────────────
// Single-regulation result panels
// ──────────────────────────────────────────────

function SingleRegResult({
  report,
  email,
  scrollToEmail,
}: {
  report: AssessResult | RegulationReport;
  email: string;
  scrollToEmail: () => void;
}) {
  const r = report as AssessResult;
  const hasSubmissionId = "submission_id" in r;
  const emailDelivery = hasSubmissionId ? r.email_delivery : "none";

  return (
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
          {!email.trim() ? (
            <button
              type="button"
              onClick={scrollToEmail}
              className="ml-2 text-sm font-medium text-sky-700 underline-offset-4 hover:underline dark:text-sky-400"
            >
              Email this report
            </button>
          ) : null}
        </div>
        {emailDelivery === "sent" ? (
          <p className="text-sm text-emerald-700 dark:text-emerald-400">
            A detailed copy was sent to your email.
          </p>
        ) : null}
        {emailDelivery === "failed" ? (
          <p className="text-sm text-amber-800 dark:text-amber-300">
            We couldn&apos;t send email — your report is still shown below.
          </p>
        ) : null}
        {emailDelivery === "misconfigured" && email.trim() ? (
          <p className="text-sm text-amber-800 dark:text-amber-300">
            Email delivery isn&apos;t configured on the server yet — your report appears below.
          </p>
        ) : null}
      </div>

      <RegScoreCard report={report as RegulationReport} />

      <div className="report-enter-delay-2 grid gap-6 lg:grid-cols-2">
        <GapsCard gaps={r.critical_gaps} />
        <RiskCard report={r} />
      </div>

      <div className="report-enter-delay-3 rounded-2xl border border-black/5 bg-white/80 p-6 dark:border-white/10 dark:bg-neutral-950/50">
        <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
          Recommended next steps
        </h3>
        <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm text-neutral-700 dark:text-neutral-300">
          {r.next_steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </div>

      <CtaCard report={r} />
    </section>
  );
}

function RegScoreCard({ report: r }: { report: RegulationReport }) {
  return (
    <div
      className={`report-enter rounded-2xl border p-6 sm:p-8 ${bandStyles[r.band as ReportBand].card}`}
    >
      <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
            {r.regulation_code
              ? (
                  {
                    eu_ai_act: "EU AI Act readiness",
                    gdpr: "GDPR compliance",
                    nist_ai_rmf: "NIST AI RMF alignment",
                    iso_42001: "ISO 42001 readiness",
                  }[r.regulation_code] ?? r.regulation_code
                )
              : "Your readiness"}
          </p>
          <p className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-4xl font-semibold tabular-nums tracking-tight text-neutral-900 dark:text-neutral-50">
            <span>{r.score_percent}%</span>
            <span
              className={[
                "inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold uppercase tracking-wide",
                r.band === "green"
                  ? "bg-emerald-600 text-white dark:bg-emerald-500"
                  : r.band === "yellow"
                    ? "bg-amber-500 text-neutral-900 dark:bg-amber-400"
                    : r.band === "orange"
                      ? "bg-orange-500 text-white dark:bg-orange-600"
                      : "bg-rose-600 text-white dark:bg-rose-500",
              ].join(" ")}
            >
              {bandShortLabel(r.band_label)}
            </span>
          </p>
          <p className="mt-3 max-w-prose text-sm leading-relaxed text-neutral-600 dark:text-neutral-300">
            {r.band_summary}
          </p>
        </div>
        <div className="w-full sm:max-w-xs">
          <div className="h-2.5 overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
            <div
              className={`report-bar-fill h-full rounded-full bg-gradient-to-r ${bandStyles[r.band as ReportBand].bar}`}
              style={{ width: `${Math.min(100, Math.max(0, r.score_percent))}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
            Model score: {r.score_points} / {r.regulation_code === "eu_ai_act" ? 20 : 15}{" "}
            weighted points
          </p>
        </div>
      </div>
    </div>
  );
}

function GapsCard({ gaps }: { gaps: string[] }) {
  return (
    <div className="rounded-2xl border border-black/5 bg-white/80 p-6 dark:border-white/10 dark:bg-neutral-950/50">
      <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
        Critical gaps
      </h3>
      {gaps.length ? (
        <ul className="mt-3 space-y-2 text-sm text-neutral-700 dark:text-neutral-300">
          {gaps.map((g) => (
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
  );
}

function RiskCard({ report: r }: { report: RegulationReport }) {
  return (
    <div className="rounded-2xl border border-black/5 bg-white/80 p-6 dark:border-white/10 dark:bg-neutral-950/50">
      <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
        Risk snapshot
      </h3>
      <ul className="mt-3 space-y-2 text-sm text-neutral-700 dark:text-neutral-300">
        <li className="flex gap-2">
          <span
            className={`${bandStyles[r.band as ReportBand].dot} mt-1.5 h-2 w-2 shrink-0 rounded-full`}
          />
          <span>{r.risk_line}</span>
        </li>
        {r.deadline ? (
          <li className="flex gap-2 text-neutral-600 dark:text-neutral-400">
            <span className="mt-0.5" aria-hidden>
              ⏰
            </span>
            <span>
              Time to key deadline ({r.deadline}):{" "}
              <strong className="text-neutral-800 dark:text-neutral-200">
                {r.days_remaining} days
              </strong>
            </span>
          </li>
        ) : null}
        <li className="flex gap-2 text-neutral-600 dark:text-neutral-400">
          <span className="mt-0.5" aria-hidden>
            📊
          </span>
          <span>
            Estimated remediation effort:{" "}
            <strong className="text-neutral-800 dark:text-neutral-200">
              {r.estimated_hours} hours
            </strong>
          </span>
        </li>
      </ul>
    </div>
  );
}

function CtaCard({ report: r }: { report: RegulationReport }) {
  return (
    <div className="report-enter-delay-4 rounded-2xl border border-dashed border-sky-300/60 bg-sky-50/50 p-6 dark:border-sky-800/50 dark:bg-sky-950/20">
      <h3 className="text-sm font-semibold text-sky-950 dark:text-sky-100">Need help?</h3>
      <div className="mt-3 flex flex-col gap-2 text-sm text-sky-900/90 dark:text-sky-200/90">
        <a
          href={r.calendly_url}
          className="font-medium underline-offset-4 hover:underline"
          target="_blank"
          rel="noreferrer"
        >
          Schedule a free consultation (Calendly)
        </a>
        <a
          href={r.website_url}
          className="font-medium underline-offset-4 hover:underline"
          target="_blank"
          rel="noreferrer"
        >
          Beacon Watchtower (website)
        </a>
        <a
          href={r.waitlist_url}
          className="font-medium underline-offset-4 hover:underline"
          target="_blank"
          rel="noreferrer"
        >
          Get early access — join the waitlist
        </a>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────
// Multi-regulation result
// ──────────────────────────────────────────────

function MultiRegResult({
  result,
  email,
  scrollToEmail,
}: {
  result: AssessResult;
  email: string;
  scrollToEmail: () => void;
}) {
  const regReports = result.regulations ?? {};
  const overallBand = (result.overall_band ?? "red") as ReportBand;

  const REG_NAMES: Record<string, string> = {
    eu_ai_act: "EU AI Act",
    gdpr: "GDPR",
    nist_ai_rmf: "NIST AI RMF",
    iso_42001: "ISO 42001",
  };

  return (
    <section
      id="results"
      className="report-enter-delay-1 mt-12 space-y-6 scroll-mt-24 border-t border-black/5 pt-10 dark:border-white/10"
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-neutral-900 dark:bg-neutral-100" />
          <h2 className="text-xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-50">
            Multi-regulation report
          </h2>
          {!email.trim() ? (
            <button
              type="button"
              onClick={scrollToEmail}
              className="ml-2 text-sm font-medium text-sky-700 underline-offset-4 hover:underline dark:text-sky-400"
            >
              Email this report
            </button>
          ) : null}
        </div>
        {result.email_delivery === "sent" ? (
          <p className="text-sm text-emerald-700 dark:text-emerald-400">
            A detailed copy was sent to your email.
          </p>
        ) : null}
      </div>

      {/* Overall posture banner */}
      <div
        className={`report-enter rounded-2xl border p-5 sm:p-6 ${bandStyles[overallBand].card}`}
      >
        <p className="text-xs font-medium uppercase tracking-wide text-neutral-500 dark:text-neutral-400">
          Overall compliance posture
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <span
            className={[
              "inline-flex items-center rounded-full px-4 py-1.5 text-sm font-semibold uppercase tracking-wide",
              overallBand === "green"
                ? "bg-emerald-600 text-white"
                : overallBand === "yellow"
                  ? "bg-amber-500 text-neutral-900"
                  : overallBand === "orange"
                    ? "bg-orange-500 text-white"
                    : "bg-rose-600 text-white",
            ].join(" ")}
          >
            {overallBand.toUpperCase()}
          </span>
          <span className="text-sm text-neutral-600 dark:text-neutral-300">
            Based on worst-band across all selected regulations
          </span>
        </div>
      </div>

      {/* Per-regulation score cards */}
      <div className="grid gap-4 lg:grid-cols-2">
        {Object.entries(regReports).map(([code, reg]) => (
          <div
            key={code}
            className={`rounded-2xl border p-5 ${bandStyles[(reg.band ?? "red") as ReportBand].card}`}
          >
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-neutral-500 dark:text-neutral-400">
              {REG_NAMES[code] ?? code}
            </p>
            <div className="flex items-baseline gap-3">
              <span className="text-3xl font-semibold tabular-nums text-neutral-900 dark:text-neutral-50">
                {reg.score_percent}%
              </span>
              <span
                className={[
                  "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide",
                  reg.band === "green"
                    ? "bg-emerald-600 text-white"
                    : reg.band === "yellow"
                      ? "bg-amber-500 text-neutral-900"
                      : reg.band === "orange"
                        ? "bg-orange-500 text-white"
                        : "bg-rose-600 text-white",
                ].join(" ")}
              >
                {bandShortLabel(reg.band_label)}
              </span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
              <div
                className={`h-full rounded-full bg-gradient-to-r ${bandStyles[(reg.band ?? "red") as ReportBand].bar}`}
                style={{ width: `${Math.min(100, Math.max(0, reg.score_percent))}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-neutral-600 dark:text-neutral-400">
              {reg.band_summary}
            </p>
            {reg.by_section && reg.by_section.length > 0 ? (
              <div className="mt-4 space-y-2">
                {reg.by_section.map((sec) => (
                  <div key={sec.section}>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-neutral-600 dark:text-neutral-400">{sec.title}</span>
                      <span className="tabular-nums text-neutral-800 dark:text-neutral-200">
                        {sec.score_raw}/{sec.score_max}
                      </span>
                    </div>
                    <div className="mt-0.5 h-1.5 overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
                      <div
                        className={`h-full rounded-full bg-gradient-to-r ${bandStyles[(reg.band ?? "red") as ReportBand].bar}`}
                        style={{ width: `${sec.score_pct}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ))}
      </div>

      {/* Combined gaps */}
      <div className="report-enter-delay-2 grid gap-6 lg:grid-cols-2">
        <GapsCard gaps={result.combined_gaps ?? []} />
        <div className="rounded-2xl border border-black/5 bg-white/80 p-6 dark:border-white/10 dark:bg-neutral-950/50">
          <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
            Remediation overview
          </h3>
          <ul className="mt-3 space-y-3">
            {Object.entries(regReports).map(([code, reg]) => (
              <li key={code} className="text-sm text-neutral-700 dark:text-neutral-300">
                <span className="font-medium">{REG_NAMES[code] ?? code}:</span>{" "}
                ~{reg.estimated_hours} hours
                {reg.deadline ? ` · deadline ${reg.deadline}` : ""}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Next steps per regulation */}
      {Object.entries(regReports).map(([code, reg]) =>
        reg.next_steps && reg.next_steps.length > 0 ? (
          <div
            key={code}
            className="report-enter-delay-3 rounded-2xl border border-black/5 bg-white/80 p-6 dark:border-white/10 dark:bg-neutral-950/50"
          >
            <h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-50">
              {REG_NAMES[code] ?? code} — Recommended next steps
            </h3>
            <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm text-neutral-700 dark:text-neutral-300">
              {reg.next_steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>
        ) : null
      )}

      {/* CTA — use first reg's links */}
      {Object.values(regReports).length > 0 ? (
        <CtaCard report={Object.values(regReports)[0]} />
      ) : null}
    </section>
  );
}

// ──────────────────────────────────────────────
// Main component
// ──────────────────────────────────────────────

export default function Home() {
  const [screen, setScreen] = useState<Screen>("landing");
  const [selectedRegCodes, setSelectedRegCodes] = useState<string[]>(["eu_ai_act"]);
  const [questions, setQuestions] = useState<Question[] | null>(null);
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

  // Load questions when moving from reg-select → assessment
  useEffect(() => {
    if (screen !== "assessment") return;
    setQuestions(null);
    setLoadError(null);

    const useLegacy =
      selectedRegCodes.length === 1 && selectedRegCodes[0] === "eu_ai_act";

    fetchQuestions(useLegacy ? undefined : selectedRegCodes)
      .then(setQuestions)
      .catch(() => setLoadError("Unable to load questionnaire. Is the API running?"));
  }, [screen, selectedRegCodes]);

  // Group questions by regulation+section for rendering
  const grouped = useMemo(() => {
    if (!questions) return new Map<string, Question[]>();
    const map = new Map<string, Question[]>();
    for (const q of questions) {
      const key = sectionKey(q.regulation_code, q.section);
      const list = map.get(key) ?? [];
      list.push(q);
      map.set(key, list);
    }
    return map;
  }, [questions]);

  const totalQuestions = useMemo(() => {
    if (!questions) return 0;
    return questions.filter((q) => visible(q, answers)).length;
  }, [questions, answers]);

  const answeredCount = useMemo(() => {
    if (!questions) return 0;
    let n = 0;
    for (const q of questions) {
      if (!visible(q, answers)) continue;
      // Legacy q8 skip
      if (q.id === "q8" && answers["q7"] === "no") { n++; continue; }
      // DB eu_q8 skip
      if (q.id === "eu_q8" && answers["eu_q7"] === "no") { n++; continue; }
      const v = answers[q.id];
      if (q.type === "multi" && Array.isArray(v) && v.length > 0) n++;
      if (q.type === "single" && typeof v === "string" && v) n++;
    }
    return n;
  }, [questions, answers]);

  const setSingle = (id: string, value: string) => {
    setAnswers((prev) => {
      const next = { ...prev, [id]: value };
      // Clear conditional q8 (legacy or DB)
      if (id === "q7" && value === "no") delete next["q8"];
      if (id === "eu_q7" && value === "no") delete next["eu_q8"];
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
        if (!questions) {
          setFormError("Questionnaire is still loading. Please try again in a moment.");
          setSubmitting(false);
          return;
        }
        const payload: Answers = { ...answers };
        for (const q of questions) {
          if (!visible(q, payload)) {
            if (q.id === "q8" || q.id === "eu_q8") delete payload[q.id];
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
          typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;

        const useLegacy =
          selectedRegCodes.length === 1 && selectedRegCodes[0] === "eu_ai_act";

        const res = await submitAssessment({
          answers: payload,
          email: email.trim() || null,
          consent,
          regulation_codes: useLegacy ? [] : selectedRegCodes,
          contact_name: contactName.trim() || null,
          company: company.trim() || null,
          client_referrer:
            typeof document !== "undefined" && document.referrer ? document.referrer : null,
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
        setFormError(err instanceof Error ? err.message : "Something went wrong. Try again.");
      } finally {
        setSubmitting(false);
      }
    },
    [answers, questions, consent, email, contactName, company, selectedRegCodes]
  );

  const scrollToEmail = () => {
    document.getElementById("contact")?.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => {
      (document.getElementById("email") as HTMLInputElement | null)?.focus();
    }, 250);
  };

  const reset = () => {
    setAnswers({});
    setResult(null);
    setFormError(null);
    setEmail("");
    setContactName("");
    setCompany("");
    setConsent(false);
    setScreen("landing");
    setSelectedRegCodes(["eu_ai_act"]);
  };

  // ── Screen routing ────────────────────────────

  if (screen === "landing") {
    return (
      <>
        <LandingScreen onStart={() => setScreen("reg-select")} onAdmin={() => setAdminOpen(true)} />
        <AdminModal open={adminOpen} onClose={() => setAdminOpen(false)} />
      </>
    );
  }

  if (screen === "reg-select") {
    return (
      <>
        <RegulationSelectorScreen
          onContinue={(codes) => {
            setSelectedRegCodes(codes);
            setScreen("assessment");
            setTimeout(() => {
              document.getElementById("questionnaire")?.scrollIntoView({ behavior: "smooth" });
            }, 50);
          }}
          onBack={() => setScreen("landing")}
        />
        <AdminModal open={adminOpen} onClose={() => setAdminOpen(false)} />
      </>
    );
  }

  // Assessment screen

  if (loadError) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="max-w-md rounded-2xl border border-rose-200/60 bg-rose-50/50 p-6 text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/20 dark:text-rose-200">
          <p className="font-medium">{loadError}</p>
          <p className="mt-2 text-sm text-rose-700/80 dark:text-rose-300/80">
            Restart the API after updating.{" "}
            <code className="rounded bg-rose-100/80 px-1.5 py-0.5 text-xs dark:bg-rose-900/40">
              cd backend &amp;&amp; uvicorn app.main:app --reload --port 8060
            </code>
          </p>
        </div>
      </div>
    );
  }

  if (!questions) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-700 dark:border-neutral-600 dark:border-t-neutral-200" />
      </div>
    );
  }

  const regLabel: Record<string, string> = {
    eu_ai_act: "EU AI Act",
    gdpr: "GDPR",
    nist_ai_rmf: "NIST AI RMF",
    iso_42001: "ISO 42001",
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(1200px_600px_at_50%_-10%,#dbeafe_0%,transparent_55%),radial-gradient(900px_500px_at_100%_20%,#fef3c7_0%,transparent_45%),var(--background)] dark:bg-[radial-gradient(1200px_600px_at_50%_-10%,#0c2649_0%,transparent_55%),radial-gradient(900px_500px_at_100%_20%,#3a2708_0%,transparent_45%),var(--background)]">
      <header className="border-b border-black/5 bg-white/70 backdrop-blur-md dark:border-white/10 dark:bg-black/30">
        <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 flex-1 space-y-2">
              <p className="text-xs font-medium uppercase tracking-widest text-sky-700/80 dark:text-sky-300/80">
                Free readiness snapshot
              </p>
              <h1 className="text-3xl font-semibold tracking-tight text-neutral-900 dark:text-neutral-50 sm:text-4xl">
                AI Compliance Readiness Assessment
              </h1>
              <p className="max-w-2xl text-sm leading-relaxed text-neutral-600 dark:text-neutral-300">
                Instant scoring across{" "}
                {selectedRegCodes.map((c) => regLabel[c] ?? c).join(", ")}. Not legal advice —
                consult qualified counsel for your specific systems.
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
                {!result ? (
                  <button
                    type="button"
                    onClick={() => setScreen("reg-select")}
                    className="font-medium text-sky-700 underline-offset-4 hover:underline dark:text-sky-400"
                  >
                    ← Change regulations
                  </button>
                ) : null}
                <span className="rounded-full border border-black/5 bg-white/60 px-2.5 py-1 dark:border-white/10 dark:bg-white/5">
                  {answeredCount} / {totalQuestions} answered
                </span>
                <span className="rounded-full border border-black/5 bg-white/60 px-2.5 py-1 dark:border-white/10 dark:bg-white/5">
                  {selectedRegCodes.map((c) => regLabel[c] ?? c).join(" · ")}
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
            .sort((a, b) => {
              // Sort by regulation code order, then section
              const [aReg, aSecStr] = a[0].split("::");
              const [bReg, bSecStr] = b[0].split("::");
              const regOrder = selectedRegCodes;
              const ai = regOrder.indexOf(aReg);
              const bi = regOrder.indexOf(bReg);
              if (ai !== bi) return ai - bi;
              return parseInt(aSecStr) - parseInt(bSecStr);
            })
            .map(([key, qs]) => {
              const [regCode, secStr] = key.split("::");
              const sectionNum = parseInt(secStr);
              const sectionTitle = qs[0]?.section_title ?? `Section ${sectionNum}`;
              const visibleQs = qs.filter((q) => visible(q, answers));
              if (visibleQs.length === 0) return null;
              return (
                <section
                  key={key}
                  className="rounded-2xl border border-black/5 bg-white/80 p-5 shadow-sm dark:border-white/10 dark:bg-neutral-950/50 sm:p-7"
                >
                  <div className="mb-5 flex items-baseline justify-between gap-3">
                    <div>
                      <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
                        {sectionBadge(regCode, sectionNum, sectionTitle)}
                      </h2>
                      <p className="text-xs text-neutral-500 dark:text-neutral-400">
                        {visibleQs.length} question{visibleQs.length !== 1 ? "s" : ""} in this
                        section
                      </p>
                    </div>
                  </div>

                  <div className="space-y-8">
                    {qs.map((q) => {
                      if (!visible(q, answers)) return null;
                      // Skip legacy/DB conditional q8
                      if (
                        (q.id === "q8" && answers["q7"] === "no") ||
                        (q.id === "eu_q8" && answers["eu_q7"] === "no")
                      )
                        return null;

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
                                        active
                                          ? "bg-sky-600 dark:bg-sky-400"
                                          : "bg-neutral-300 dark:bg-neutral-600",
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
              );
            })}

          {formError ? (
            <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-200">
              {formError}
            </p>
          ) : null}

          <div
            id="contact"
            className="rounded-2xl border border-black/5 bg-white/80 p-5 dark:border-white/10 dark:bg-neutral-950/50 sm:p-6"
          >
            <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
              Contact (optional)
            </p>
            <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
              Helps us follow up. Email can stay blank if you only want the on-screen report.
            </p>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div>
                <label
                  className="text-xs text-neutral-600 dark:text-neutral-400"
                  htmlFor="contact-name"
                >
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
                <label
                  className="text-xs text-neutral-600 dark:text-neutral-400"
                  htmlFor="company"
                >
                  Organisation
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
              id="email"
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
          result.multi_regulation ? (
            <MultiRegResult result={result} email={email} scrollToEmail={scrollToEmail} />
          ) : (
            <SingleRegResult report={result} email={email} scrollToEmail={scrollToEmail} />
          )
        ) : null}
      </main>

      <footer className="border-t border-black/5 py-10 text-center text-xs leading-relaxed text-neutral-500 dark:border-white/10 dark:text-neutral-500">
        <p>
          Readiness bands: 18–20 strong (green), 15–17 minor gaps (yellow), 12–14 significant gaps
          (orange), below 12 high risk (red). Scoring uses weighted answers — not a legal
          determination.
        </p>
        <p className="mt-3">For educational planning only — not legal advice.</p>
      </footer>

      <AdminModal open={adminOpen} onClose={() => setAdminOpen(false)} />
    </div>
  );
}
