"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import {
  adminExportCsvBlob,
  adminLogin,
  clearAdminToken,
  fetchAdminSubmissions,
  fetchAdminSummary,
  getAdminToken,
  type AdminSubmission,
  type AdminSummary,
} from "@/lib/api";

const DEFAULT_ADMIN_EMAIL =
  process.env.NEXT_PUBLIC_ADMIN_EMAIL || "beaconone.org@gmail.com";

type Props = {
  open: boolean;
  onClose: () => void;
};

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function AdminModal({ open, onClose }: Props) {
  const [email, setEmail] = useState(DEFAULT_ADMIN_EMAIL);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [submissions, setSubmissions] = useState<AdminSubmission[] | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, sub] = await Promise.all([
        fetchAdminSummary(),
        fetchAdminSubmissions(100, 0),
      ]);
      setSummary(s);
      setSubmissions(sub);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data.");
      setSummary(null);
      setSubmissions(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    setError(null);
    if (getAdminToken()) {
      void loadData();
    } else {
      setSummary(null);
      setSubmissions(null);
    }
  }, [open, loadData]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const onLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await adminLogin(email.trim(), password);
      setPassword("");
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  };

  const onLogout = () => {
    clearAdminToken();
    setSummary(null);
    setSubmissions(null);
    setPassword("");
    setError(null);
  };

  const onDownloadCsv = async () => {
    setError(null);
    setLoading(true);
    try {
      const blob = await adminExportCsvBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "assessment_submissions.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed.");
    } finally {
      setLoading(false);
    }
  };

  const metaStr = (s: AdminSubmission) => {
    const m = s.meta || {};
    const name = typeof m.contact_name === "string" ? m.contact_name : "";
    const co = typeof m.company === "string" ? m.company : "";
    return [name, co].filter(Boolean).join(" · ") || "—";
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/45 p-4 pt-[10vh] backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="admin-modal-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-4xl rounded-2xl border border-black/10 bg-white shadow-xl dark:border-white/10 dark:bg-neutral-950"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-black/5 px-5 py-4 dark:border-white/10">
          <h2
            id="admin-modal-title"
            className="text-lg font-semibold text-neutral-900 dark:text-neutral-50"
          >
            Admin — submissions
          </h2>
          <div className="flex items-center gap-2">
            {getAdminToken() ? (
              <button
                type="button"
                onClick={onDownloadCsv}
                disabled={loading}
                className="rounded-lg border border-black/10 bg-white px-3 py-1.5 text-sm font-medium text-neutral-800 transition hover:bg-neutral-50 disabled:opacity-50 dark:border-white/15 dark:bg-neutral-900 dark:text-neutral-100 dark:hover:bg-neutral-800"
              >
                Download CSV
              </button>
            ) : null}
            {getAdminToken() ? (
              <button
                type="button"
                onClick={onLogout}
                className="rounded-lg border border-black/10 px-3 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 dark:border-white/15 dark:text-neutral-300 dark:hover:bg-neutral-900"
              >
                Log out
              </button>
            ) : null}
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg p-1.5 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="max-h-[min(70vh,720px)] overflow-y-auto p-5">
          {error ? (
            <p className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-200">
              {error}
            </p>
          ) : null}

          {!getAdminToken() ? (
            <form onSubmit={onLogin} className="mx-auto max-w-sm space-y-4">
              <p className="text-sm text-neutral-600 dark:text-neutral-400">
                Sign in with the admin email and password configured on the API
                (see <code className="text-xs">ADMIN_EMAIL</code> /{" "}
                <code className="text-xs">ADMIN_PASSWORD</code>).
              </p>
              <div>
                <label
                  className="text-xs font-medium text-neutral-600 dark:text-neutral-400"
                  htmlFor="admin-email"
                >
                  Email
                </label>
                <input
                  id="admin-email"
                  type="email"
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm dark:border-white/10 dark:bg-neutral-900"
                />
              </div>
              <div>
                <label
                  className="text-xs font-medium text-neutral-600 dark:text-neutral-400"
                  htmlFor="admin-password"
                >
                  Password
                </label>
                <input
                  id="admin-password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm dark:border-white/10 dark:bg-neutral-900"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-xl bg-neutral-900 py-2.5 text-sm font-medium text-white disabled:opacity-50 dark:bg-neutral-100 dark:text-neutral-900"
              >
                {loading ? "Signing in…" : "Sign in"}
              </button>
            </form>
          ) : loading && !summary ? (
            <div className="flex justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-700 dark:border-neutral-600 dark:border-t-neutral-200" />
            </div>
          ) : (
            <div className="space-y-6">
              {summary ? (
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border border-black/5 bg-neutral-50/80 px-4 py-3 dark:border-white/10 dark:bg-neutral-900/50">
                    <p className="text-xs text-neutral-500">Total</p>
                    <p className="text-2xl font-semibold tabular-nums">{summary.total}</p>
                  </div>
                  <div className="rounded-xl border border-black/5 bg-neutral-50/80 px-4 py-3 dark:border-white/10 dark:bg-neutral-900/50">
                    <p className="text-xs text-neutral-500">With email</p>
                    <p className="text-2xl font-semibold tabular-nums">
                      {summary.with_email}
                    </p>
                  </div>
                  <div className="rounded-xl border border-black/5 bg-neutral-50/80 px-4 py-3 dark:border-white/10 dark:bg-neutral-900/50">
                    <p className="text-xs text-neutral-500">By band (count)</p>
                    <p className="text-sm text-neutral-700 dark:text-neutral-300">
                      {Object.entries(summary.by_band)
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(" · ") || "—"}
                    </p>
                  </div>
                </div>
              ) : null}

              {submissions && submissions.length > 0 ? (
                <div className="overflow-x-auto rounded-xl border border-black/5 dark:border-white/10">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead className="border-b border-black/5 bg-neutral-50/80 text-xs uppercase text-neutral-500 dark:border-white/10 dark:bg-neutral-900/60">
                      <tr>
                        <th className="px-3 py-2">ID</th>
                        <th className="px-3 py-2">When</th>
                        <th className="px-3 py-2">Email</th>
                        <th className="px-3 py-2">Band</th>
                        <th className="px-3 py-2">%</th>
                        <th className="px-3 py-2">Contact / org</th>
                        <th className="px-3 py-2 w-24" />
                      </tr>
                    </thead>
                    <tbody>
                      {submissions.map((s) => {
                        const rep = s.report as Record<string, unknown>;
                        const band = String(rep.band ?? "");
                        const pct = rep.score_percent;
                        return (
                          <Fragment key={s.id}>
                            <tr className="border-b border-black/5 dark:border-white/5">
                              <td className="px-3 py-2 font-mono text-xs">{s.id}</td>
                              <td className="px-3 py-2 text-xs text-neutral-600 dark:text-neutral-400">
                                {fmtDate(s.created_at)}
                              </td>
                              <td className="max-w-[140px] truncate px-3 py-2 text-xs">
                                {s.email || "—"}
                              </td>
                              <td className="px-3 py-2 text-xs">{band}</td>
                              <td className="px-3 py-2 text-xs tabular-nums">{String(pct ?? "—")}</td>
                              <td className="max-w-[180px] truncate px-3 py-2 text-xs text-neutral-600 dark:text-neutral-400">
                                {metaStr(s)}
                              </td>
                              <td className="px-3 py-2">
                                <button
                                  type="button"
                                  onClick={() =>
                                    setExpandedId(expandedId === s.id ? null : s.id)
                                  }
                                  className="text-xs font-medium text-sky-700 underline-offset-2 hover:underline dark:text-sky-400"
                                >
                                  {expandedId === s.id ? "Hide" : "Details"}
                                </button>
                              </td>
                            </tr>
                            {expandedId === s.id ? (
                              <tr className="bg-neutral-50/50 dark:bg-neutral-900/30">
                                <td colSpan={7} className="px-3 py-3">
                                  <pre className="max-h-48 overflow-auto rounded-lg border border-black/5 bg-white p-3 text-[11px] leading-relaxed dark:border-white/10 dark:bg-neutral-950">
                                    {JSON.stringify(
                                      {
                                        answers: s.answers,
                                        report: s.report,
                                        meta: s.meta,
                                        consent: s.consent,
                                      },
                                      null,
                                      2
                                    )}
                                  </pre>
                                </td>
                              </tr>
                            ) : null}
                          </Fragment>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : !loading ? (
                <p className="text-sm text-neutral-500">No submissions yet.</p>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
