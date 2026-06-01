"""
Regulation-aware scoring engine.
Works with normalized question dicts (same format as QUESTIONS_INTERNAL).
"""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

EU_AI_ACT_DEADLINE = date(2026, 8, 2)

BandKey = Literal["green", "yellow", "orange", "red"]

# Per-regulation configuration
REGULATION_CONFIG: dict[str, dict[str, Any]] = {
    "eu_ai_act": {
        "max_score": 20.0,
        "band_mode": "raw",          # thresholds on raw score
        "green": 18,
        "yellow": 15,
        "orange": 12,
        "deadline": EU_AI_ACT_DEADLINE.isoformat(),
        "fine_exposure": (
            "Fines up to €35M or 7% of global annual turnover (whichever is higher) "
            "for severe breaches of the EU AI Act."
        ),
        "calendly_url": "https://calendly.com/beaconone-org/30min",
        "website_url": "https://www.beaconone.net/ai-compliance",
        "waitlist_url": (
            "https://docs.google.com/forms/d/e/"
            "1FAIpQLScOztY5nKDrlmnmUtHDd0fEN0qifiAxFcVcDBzc8BWmpkhj9A/viewform"
        ),
        "next_steps": [
            "Create or validate an AI system inventory (Week 1)",
            "Classify systems against EU AI Act categories (Week 2–3)",
            "Stand up risk management & documentation for high-risk systems (Week 4–6)",
            "Complete technical documentation packs (Week 5–8)",
            "Plan conformity assessment / notified body route where required (Week 9–11)",
        ],
    },
    "gdpr": {
        "max_score": 15.0,
        "band_mode": "pct",          # thresholds on score_percent
        "green": 90,
        "yellow": 75,
        "orange": 60,
        "deadline": None,
        "fine_exposure": (
            "Fines up to €20M or 4% of global annual turnover (whichever is higher) "
            "for serious GDPR infringements."
        ),
        "calendly_url": "https://calendly.com/beaconone-org/30min",
        "website_url": "https://www.beaconone.net/ai-compliance",
        "waitlist_url": (
            "https://docs.google.com/forms/d/e/"
            "1FAIpQLScOztY5nKDrlmnmUtHDd0fEN0qifiAxFcVcDBzc8BWmpkhj9A/viewform"
        ),
        "next_steps": [
            "Complete or update your Records of Processing Activities (RoPA) (Week 1)",
            "Verify lawful basis for every processing activity (Week 1–2)",
            "Implement and test Subject Access Request (SAR) response procedures (Week 2–3)",
            "Conduct DPIAs for high-risk processing: AI profiling, biometrics, surveillance (Week 3–5)",
            "Review and update international data transfer mechanisms (SCCs / adequacy) (Week 5–7)",
        ],
    },
    "nist_ai_rmf": {
        "max_score": 15.0,
        "band_mode": "raw",
        "green": 13,
        "yellow": 10,
        "orange": 7,
        "deadline": None,
        "fine_exposure": None,
        "risk_note": (
            "NIST AI RMF alignment is increasingly required by US federal agency AI "
            "procurement and enterprise B2B buyers."
        ),
        "calendly_url": "https://calendly.com/beaconone-org/30min",
        "website_url": "https://www.beaconone.net/ai-compliance",
        "waitlist_url": (
            "https://docs.google.com/forms/d/e/"
            "1FAIpQLScOztY5nKDrlmnmUtHDd0fEN0qifiAxFcVcDBzc8BWmpkhj9A/viewform"
        ),
        "next_steps": [
            "Develop or formalise an AI risk management policy with defined roles (Week 1–2)",
            "Catalogue AI use cases with context-of-use and impact assessments (Week 2–3)",
            "Establish quantitative metrics for bias, drift, and adversarial robustness (Week 3–5)",
            "Run red-team / adversarial testing on high-risk AI systems (Week 5–7)",
            "Create and rehearse an AI incident response playbook with rollback procedures (Week 7–9)",
        ],
    },
    "iso_42001": {
        "max_score": 20.0,
        "band_mode": "pct",
        "green": 90,
        "yellow": 75,
        "orange": 60,
        "deadline": None,
        "fine_exposure": None,
        "calendly_url": "https://calendly.com/beaconone-org/30min",
        "website_url": "https://www.beaconone.net/ai-compliance",
        "waitlist_url": (
            "https://docs.google.com/forms/d/e/"
            "1FAIpQLScOztY5nKDrlmnmUtHDd0fEN0qifiAxFcVcDBzc8BWmpkhj9A/viewform"
        ),
        "next_steps": [],
    },
}

BAND_LABELS: dict[BandKey, str] = {
    "green": "GREEN — Compliant",
    "yellow": "YELLOW — Minor gaps",
    "orange": "ORANGE — Significant gaps",
    "red": "RED — High risk",
}

NIST_TIER_LABELS: dict[BandKey, str] = {
    "green": "GREEN — Tier 4 (Adaptive)",
    "yellow": "YELLOW — Tier 3 (Repeatable)",
    "orange": "ORANGE — Tier 2 (Structured)",
    "red": "RED — Tier 1 (Partial)",
}


def _visible(q: dict[str, Any], answers: dict[str, Any]) -> bool:
    cond = q.get("show_if")
    if not cond:
        return True
    ref = answers.get(cond["question_id"])
    if isinstance(ref, list):
        return False
    return ref in cond["values"]


def _score_question(q: dict[str, Any], raw: Any) -> float:
    """Score a single question; handles multi-select summing and none-option."""
    qtype = q["type"]

    if qtype == "multi":
        if not isinstance(raw, list) or len(raw) == 0:
            return 0.0
        selected = set(raw)
        non_none_selected = {v for v in selected if v != "none"}
        if not non_none_selected:
            return 0.0
        # Sum points from selected non-none options
        pts = sum(
            float(o.get("points", 0))
            for o in q["options"]
            if o["value"] in non_none_selected
        )
        # If all options have 0 points (informational / flag questions like eu_q8),
        # any selection = 1.0 (presence of answer = compliant response)
        all_zero = all(float(o.get("points", 0)) == 0.0 for o in q["options"] if o["value"] != "none")
        if all_zero:
            return 1.0
        return min(1.0, pts)

    # single
    if raw is None or isinstance(raw, list):
        return 0.0
    for opt in q["options"]:
        if opt["value"] == raw:
            return float(opt.get("points", 0))
    return 0.0


def _max_score_question(q: dict[str, Any]) -> float:
    """Max achievable points for a question."""
    opts = q.get("options", [])
    if not opts:
        return 0.0
    if q["type"] == "multi":
        # Max = sum of all non-none options, capped at 1.0
        pts = sum(
            float(o.get("points", 0)) for o in opts if o["value"] != "none"
        )
        return min(1.0, pts)
    return max(float(o.get("points", 0)) for o in opts)


def _band(cfg: dict[str, Any], score_raw: float, score_pct: int) -> BandKey:
    comparand = score_raw if cfg["band_mode"] == "raw" else score_pct
    if comparand >= cfg["green"]:
        return "green"
    if comparand >= cfg["yellow"]:
        return "yellow"
    if comparand >= cfg["orange"]:
        return "orange"
    return "red"


def _band_summary(regulation_code: str, band: BandKey, score_pct: int) -> str:
    summaries: dict[str, dict[BandKey, str]] = {
        "eu_ai_act": {
            "green": f"{score_pct}% ready — strong posture against core EU AI Act readiness checks.",
            "yellow": f"{score_pct}% ready — address remaining gaps before enforcement milestones.",
            "orange": f"{score_pct}% ready — prioritize governance, documentation, and conformity workstreams.",
            "red": f"{score_pct}% ready — urgent remediation recommended ahead of regulatory deadlines.",
        },
        "gdpr": {
            "green": f"{score_pct}% — strong GDPR posture across lawful basis, rights, and security.",
            "yellow": f"{score_pct}% — address residual GDPR gaps before a supervisory authority audit.",
            "orange": f"{score_pct}% — significant GDPR gaps; prioritize rights management and DPIAs.",
            "red": f"{score_pct}% — high GDPR exposure; urgent action required across multiple obligations.",
        },
        "nist_ai_rmf": {
            "green": f"{score_pct}% — Tier 4 Adaptive: AI risk management is mature and organisation-wide.",
            "yellow": f"{score_pct}% — Tier 3 Repeatable: practices exist but need broader institutionalisation.",
            "orange": f"{score_pct}% — Tier 2 Structured: some practices in place; gaps in measurement and response.",
            "red": f"{score_pct}% — Tier 1 Partial: AI risk management is ad hoc; foundational gaps present.",
        },
    }
    default = {
        "green": f"{score_pct}% — compliant posture.",
        "yellow": f"{score_pct}% — minor gaps remain.",
        "orange": f"{score_pct}% — significant gaps.",
        "red": f"{score_pct}% — high risk posture.",
    }
    return summaries.get(regulation_code, default)[band]


def _risk_line(cfg: dict[str, Any], regulation_code: str, band: BandKey, score_pct: int) -> str:
    fine = cfg.get("fine_exposure")
    note = cfg.get("risk_note", "")
    if band == "green":
        return f"Lower acute readiness risk on this snapshot — continue monitoring."
    if band in ("yellow", "orange", "red"):
        if fine:
            severity = {"yellow": "MEDIUM RISK", "orange": "HIGH RISK", "red": "CRITICAL RISK"}[band]
            return f"{severity}: {fine}"
        if note:
            return note
    return "Readiness requires improvement — consult qualified counsel for your specific situation."


def _estimate_hours(score_raw: float, max_score: float, gap_count: int) -> int:
    if max_score <= 0:
        return 80
    base = 80 + (max_score - score_raw) * 14
    base += gap_count * 12
    return int(min(500, max(40, round(base))))


def _gap_text(q: dict[str, Any]) -> str:
    tags = q.get("article_tags") or []
    prefix = tags[0] if tags else "Gap"
    text = q["text"]
    if len(text) > 70:
        text = text[:67] + "…"
    return f"{prefix}: {text}"


def _is_gdpr_q4_gap(q: dict[str, Any], raw: Any) -> bool:
    """gdpr_q4 triggers a gap if any special category (not 'none') is selected."""
    if q["id"] != "gdpr_q4":
        return False
    if not isinstance(raw, list):
        return False
    specials = {v for v in raw if v != "none"}
    return bool(specials)


def compute_score(
    answers: dict[str, Any],
    questions: list[dict[str, Any]],
    regulation_code: str,
) -> dict[str, Any]:
    """
    Core scoring engine for any regulation.

    questions: list of normalized question dicts for this regulation.
    Returns full report dict matching (a superset of) the existing AssessResponse shape.
    """
    cfg = REGULATION_CONFIG.get(regulation_code, REGULATION_CONFIG["eu_ai_act"])

    score_raw = 0.0
    max_score = 0.0
    gaps: list[str] = []
    by_section: dict[int, dict[str, Any]] = {}

    for q in sorted(questions, key=lambda x: (x["section"], x["order"])):
        if not _visible(q, answers):
            # eu_q8: "which high-risk categories" — skipped when eu_q7="no" (not high-risk).
            # Award 1.0 full credit: answering "no" to high-risk is a compliant response.
            if q["id"] == "eu_q8":
                score_raw += 1.0
                max_score += 1.0
                sec = q["section"]
                if sec not in by_section:
                    by_section[sec] = {"title": q["section_title"], "raw": 0.0, "max": 0.0}
                by_section[sec]["raw"] += 1.0
                by_section[sec]["max"] += 1.0
            continue

        q_max = _max_score_question(q)
        raw = answers.get(q["id"])
        pts = _score_question(q, raw)

        score_raw += pts
        max_score += q_max

        sec = q["section"]
        if sec not in by_section:
            by_section[sec] = {"title": q["section_title"], "raw": 0.0, "max": 0.0}
        by_section[sec]["raw"] += pts
        by_section[sec]["max"] += q_max

        # Gap detection
        if _is_gdpr_q4_gap(q, raw):
            gaps.append(
                "Art.9: Enhanced GDPR obligations apply for special category data — "
                "explicit consent or Art.9(2) exemption required"
            )
        elif q_max > 0 and pts == 0.0:
            gaps.append(_gap_text(q))
        elif q_max > 0 and pts < q_max * 0.5:
            gaps.append(_gap_text(q))

    # Override max_score with regulation config if specified and max_score would be 0
    cfg_max = cfg["max_score"]
    if max_score == 0:
        max_score = cfg_max

    score_pct = int(round((score_raw / cfg_max) * 100)) if cfg_max > 0 else 0
    score_pct = max(0, min(100, score_pct))

    band_key = _band(cfg, score_raw, score_pct)
    band_label = (
        NIST_TIER_LABELS[band_key]
        if regulation_code == "nist_ai_rmf"
        else BAND_LABELS[band_key]
    )

    today = date.today()
    deadline_str = cfg.get("deadline") or ""
    days_remaining = 0
    if deadline_str:
        try:
            dl = date.fromisoformat(deadline_str)
            days_remaining = max(0, (dl - today).days)
        except ValueError:
            pass

    next_steps = list(cfg.get("next_steps", []))

    # Section breakdown
    section_list = [
        {
            "section": sec,
            "title": data["title"],
            "score_raw": round(data["raw"], 2),
            "score_max": round(data["max"], 2),
            "score_pct": (
                int(round((data["raw"] / data["max"]) * 100))
                if data["max"] > 0
                else 100
            ),
        }
        for sec, data in sorted(by_section.items())
    ]

    return {
        "regulation_code": regulation_code,
        "score_points": round(score_raw, 2),
        "score_percent": score_pct,
        "band": band_key,
        "band_label": band_label,
        "band_summary": _band_summary(regulation_code, band_key, score_pct),
        "critical_gaps": gaps[:8],
        "risk_line": _risk_line(cfg, regulation_code, band_key, score_pct),
        "days_remaining": days_remaining,
        "deadline": deadline_str,
        "estimated_hours": _estimate_hours(score_raw, cfg_max, len(gaps)),
        "next_steps": next_steps,
        "by_section": section_list,
        "fine_exposure": cfg.get("fine_exposure"),
        "calendly_url": cfg["calendly_url"],
        "website_url": cfg["website_url"],
        "waitlist_url": cfg["waitlist_url"],
    }


BAND_ORDER: dict[BandKey, int] = {"green": 0, "yellow": 1, "orange": 2, "red": 3}


def worst_band(bands: list[str]) -> BandKey:
    valid = [b for b in bands if b in BAND_ORDER]
    if not valid:
        return "red"
    return max(valid, key=lambda b: BAND_ORDER[b])  # type: ignore[return-value]
