export type ReportBand = "green" | "yellow" | "orange" | "red";

export const bandStyles: Record<
  ReportBand,
  { bar: string; card: string; dot: string }
> = {
  green: {
    bar: "from-emerald-500/90 to-teal-600/90",
    card: "border-emerald-200/80 bg-emerald-50/80 dark:border-emerald-900/50 dark:bg-emerald-950/30",
    dot: "bg-emerald-500",
  },
  yellow: {
    bar: "from-amber-400/90 to-yellow-500/90",
    card: "border-amber-200/80 bg-amber-50/80 dark:border-amber-900/50 dark:bg-amber-950/30",
    dot: "bg-amber-500",
  },
  orange: {
    bar: "from-orange-500/90 to-amber-600/90",
    card: "border-orange-200/80 bg-orange-50/80 dark:border-orange-900/50 dark:bg-orange-950/30",
    dot: "bg-orange-500",
  },
  red: {
    bar: "from-rose-600/90 to-red-700/90",
    card: "border-rose-200/80 bg-rose-50/80 dark:border-rose-900/50 dark:bg-rose-950/30",
    dot: "bg-rose-600",
  },
};

export function normalizeReportBand(v: unknown): ReportBand {
  const s = typeof v === "string" ? v.toLowerCase().trim() : "";
  if (s === "green" || s === "yellow" || s === "orange" || s === "red") {
    return s;
  }
  return "orange";
}

/** Short label after em dash, e.g. "ORANGE — Significant gaps" → "Significant gaps" */
export function bandShortLabel(bandLabel: unknown): string {
  const raw = typeof bandLabel === "string" ? bandLabel : "";
  const part = raw.split("—")[1]?.trim();
  return part || raw || "—";
}
