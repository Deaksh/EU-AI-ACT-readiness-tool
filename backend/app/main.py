from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env before app.db creates the SQLAlchemy engine (import-time).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import csv
import hmac
import io
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from fastapi import Depends, FastAPI, HTTPException, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.db import admin_summary_rows, init_db, list_submissions, save_submission
from app.report_email import (
    brevo_api_is_configured,
    build_report_html,
    send_report_via_brevo_api,
    send_report_via_resend,
    send_report_via_smtp,
    smtp_is_configured,
)

logger = logging.getLogger(__name__)

EU_AI_ACT_DEADLINE = date(2026, 8, 2)

QuestionType = Literal["single", "multi"]


class OptionOut(BaseModel):
    value: str
    label: str


class QuestionOut(BaseModel):
    id: str
    section: int
    section_title: str
    order: int
    text: str
    type: QuestionType
    options: list[OptionOut]
    show_if: dict[str, Any] | None = None


class AssessRequest(BaseModel):
    answers: dict[str, str | list[str]] = Field(default_factory=dict)
    email: EmailStr | None = None
    consent: bool = False
    contact_name: str | None = Field(None, max_length=120)
    company: str | None = Field(None, max_length=200)
    client_referrer: str | None = Field(None, max_length=2000)
    page_url: str | None = Field(None, max_length=2000)
    utm_source: str | None = Field(None, max_length=200)
    utm_medium: str | None = Field(None, max_length=200)
    utm_campaign: str | None = Field(None, max_length=200)

    @field_validator("email", mode="before")
    @classmethod
    def email_blank_to_none(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator(
        "contact_name",
        "company",
        "client_referrer",
        "page_url",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        mode="before",
    )
    @classmethod
    def strip_blank_optional(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s else None
        return v


class AssessResponse(BaseModel):
    score_points: float
    score_percent: int
    band: Literal["green", "yellow", "orange", "red"]
    band_label: str
    band_summary: str
    critical_gaps: list[str]
    risk_line: str
    days_remaining: int
    deadline: str
    estimated_hours: int
    next_steps: list[str]
    calendly_url: str
    website_url: str
    waitlist_url: str
    submission_id: int
    email_delivery: Literal["none", "sent", "failed", "misconfigured"]


class AdminLoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=512)


def _options(*items: tuple[str, str, float]) -> list[dict[str, Any]]:
    return [{"value": v, "label": lab, "points": pts} for v, lab, pts in items]


QUESTIONS_INTERNAL: list[dict[str, Any]] = [
    {
        "id": "q1",
        "section": 1,
        "section_title": "AI Inventory",
        "order": 1,
        "text": "Do you have a complete inventory of AI systems?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("partial", "Partial", 0.5),
            ("no", "No", 0.0),
        ),
    },
    {
        "id": "q2",
        "section": 1,
        "section_title": "AI Inventory",
        "order": 2,
        "text": "How many AI systems are in production?",
        "type": "single",
        "options": _options(
            ("0_10", "0–10", 1.0),
            ("10_50", "10–50", 0.5),
            ("50_plus", "50+", 0.5),
        ),
    },
    {
        "id": "q3",
        "section": 1,
        "section_title": "AI Inventory",
        "order": 3,
        "text": "Are AI systems documented with: purpose, data, algorithm?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("some", "Some", 0.5),
            ("no", "No", 0.0),
        ),
    },
    {
        "id": "q4",
        "section": 1,
        "section_title": "AI Inventory",
        "order": 4,
        "text": "Do you track which systems serve EU users?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("no", "No", 0.0),
            ("dont_know", "Don't know", 0.0),
        ),
    },
    {
        "id": "q5",
        "section": 1,
        "section_title": "AI Inventory",
        "order": 5,
        "text": "Are systems categorized by risk level?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("no", "No", 0.0),
            ("in_progress", "In progress", 0.5),
        ),
    },
    {
        "id": "q6",
        "section": 2,
        "section_title": "Classification",
        "order": 6,
        "text": "Have you classified systems per EU AI Act categories?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("partial", "Partial", 0.5),
            ("no", "No", 0.0),
        ),
    },
    {
        "id": "q7",
        "section": 2,
        "section_title": "Classification",
        "order": 7,
        "text": "Do you have high-risk AI systems?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("no", "No", 1.0),
            ("dont_know", "Don't know", 0.0),
        ),
    },
    {
        "id": "q8",
        "section": 2,
        "section_title": "Classification",
        "order": 8,
        "text": "If applicable, which high-risk categories apply?",
        "type": "multi",
        "show_if": {"question_id": "q7", "values": ["yes", "dont_know"]},
        "options": _options(
            ("employment", "Employment / HR", 0.0),
            ("credit", "Credit / insurance", 0.0),
            ("healthcare", "Healthcare", 0.0),
            ("law_enforcement", "Law enforcement / justice", 0.0),
            ("education", "Education", 0.0),
            ("critical_infra", "Critical infrastructure", 0.0),
            ("biometric", "Biometric identification", 0.0),
            ("other", "Other / general-purpose high-risk", 0.0),
        ),
    },
    {
        "id": "q9",
        "section": 2,
        "section_title": "Classification",
        "order": 9,
        "text": "Have you documented classification rationale?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("no", "No", 0.0),
        ),
    },
    {
        "id": "q10",
        "section": 2,
        "section_title": "Classification",
        "order": 10,
        "text": "Are prohibited AI practices identified and stopped?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("no", "No", 0.0),
            ("dont_know", "Don't know", 0.0),
        ),
    },
    {
        "id": "q11",
        "section": 3,
        "section_title": "Compliance Obligations",
        "order": 11,
        "text": "Do high-risk systems have risk management processes?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("partial", "Partial", 0.5),
            ("no", "No", 0.0),
        ),
    },
    {
        "id": "q12",
        "section": 3,
        "section_title": "Compliance Obligations",
        "order": 12,
        "text": "Is technical documentation complete and current?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("partial", "Partial", 0.5),
            ("no", "No", 0.0),
        ),
    },
    {
        "id": "q13",
        "section": 3,
        "section_title": "Compliance Obligations",
        "order": 13,
        "text": "Are data governance practices documented?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("no", "No", 0.0),
        ),
    },
    {
        "id": "q14",
        "section": 3,
        "section_title": "Compliance Obligations",
        "order": 14,
        "text": "Is human oversight implemented where required?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("no", "No", 0.0),
            ("dont_know", "Don't know", 0.0),
        ),
    },
    {
        "id": "q15",
        "section": 3,
        "section_title": "Compliance Obligations",
        "order": 15,
        "text": "Have you completed conformity assessments?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("no", "No", 0.0),
            ("in_progress", "In progress", 0.5),
        ),
    },
    {
        "id": "q16",
        "section": 4,
        "section_title": "Governance",
        "order": 16,
        "text": "Is there an AI governance committee or owner?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("no", "No", 0.0),
        ),
    },
    {
        "id": "q17",
        "section": 4,
        "section_title": "Governance",
        "order": 17,
        "text": "Are compliance responsibilities assigned?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("partial", "Partial", 0.5),
            ("no", "No", 0.0),
        ),
    },
    {
        "id": "q18",
        "section": 4,
        "section_title": "Governance",
        "order": 18,
        "text": "Do you have incident reporting processes?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("no", "No", 0.0),
        ),
    },
    {
        "id": "q19",
        "section": 4,
        "section_title": "Governance",
        "order": 19,
        "text": "Are you monitoring for system drift or bias?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("no", "No", 0.0),
            ("dont_know", "Don't know", 0.0),
        ),
    },
    {
        "id": "q20",
        "section": 4,
        "section_title": "Governance",
        "order": 20,
        "text": "Are you ready for an EU regulator audit?",
        "type": "single",
        "options": _options(
            ("yes", "Yes", 1.0),
            ("no", "No", 0.0),
            ("not_sure", "Not sure", 0.0),
        ),
    },
]

def _visible(q: dict[str, Any], answers: dict[str, str | list[str]]) -> bool:
    cond = q.get("show_if")
    if not cond:
        return True
    ref = answers.get(cond["question_id"])
    if isinstance(ref, list):
        return False
    return ref in cond["values"]


def _points_for_answer(q: dict[str, Any], raw: str | list[str] | None) -> float:
    if q["type"] == "multi":
        if not isinstance(raw, list):
            return 0.0
        return 1.0 if len(raw) > 0 else 0.0

    if raw is None or isinstance(raw, list):
        return 0.0

    for opt in q["options"]:
        if opt["value"] == raw:
            return float(opt["points"])
    return 0.0


def _score_total(answers: dict[str, str | list[str]]) -> float:
    total = 0.0
    for q in QUESTIONS_INTERNAL:
        if not _visible(q, answers):
            if q["id"] == "q8":
                total += 1.0
            continue

        raw = answers.get(q["id"])
        if q["id"] == "q8":
            total += _points_for_answer(q, raw)
            continue

        total += _points_for_answer(q, raw)

    return total


def _band_from_points(total: float) -> tuple[Literal["green", "yellow", "orange", "red"], str, str]:
    rounded = int(round(total))
    pct = int(round((total / 20.0) * 100))

    if rounded >= 18:
        return (
            "green",
            "GREEN — Compliant",
            f"{pct}% ready — strong posture against core EU AI Act readiness checks.",
        )
    if rounded >= 15:
        return (
            "yellow",
            "YELLOW — Minor gaps",
            f"{pct}% ready — address remaining gaps before enforcement milestones.",
        )
    if rounded >= 12:
        return (
            "orange",
            "ORANGE — Significant gaps",
            f"{pct}% ready — prioritize governance, documentation, and conformity workstreams.",
        )
    return (
        "red",
        "RED — High risk",
        f"{pct}% ready — urgent remediation recommended ahead of regulatory deadlines.",
    )


def _collect_gaps(answers: dict[str, str | list[str]]) -> list[str]:
    gaps: list[str] = []

    def s(qid: str) -> str | list[str] | None:
        return answers.get(qid)

    if s("q1") in (None, "no", "partial"):
        gaps.append("No complete AI inventory")
    if s("q6") in (None, "no", "partial"):
        gaps.append("High-risk / EU categories not fully classified")
    if s("q7") == "dont_know":
        gaps.append("High-risk exposure unclear")
    if s("q12") in (None, "no", "partial"):
        gaps.append("Missing or incomplete technical documentation")
    if s("q15") in (None, "no"):
        gaps.append("No conformity assessments completed")
    if s("q10") in (None, "no", "dont_know"):
        gaps.append("Prohibited practices screening not verified")
    if s("q4") in (None, "no", "dont_know"):
        gaps.append("EU user scope not reliably tracked")
    if s("q20") in (None, "no", "not_sure"):
        gaps.append("Audit readiness not demonstrated")

    q7 = s("q7")
    if q7 in ("yes", "dont_know") and isinstance(s("q8"), list) and len(s("q8")) == 0:
        gaps.append("High-risk categories not specified")

    return gaps[:8]


def _risk_line(band: str, score_percent: int) -> str:
    if band == "green":
        return "Lower acute readiness risk on this snapshot — continue monitoring drift and updates."
    if band == "yellow":
        return (
            f"MEDIUM RISK: Non-compliance exposure remains material — fines can reach up to "
            f"€35M or 7% of global annual turnover (whichever is higher) for severe breaches."
        )
    if band == "orange":
        return (
            f"HIGH RISK: Potential €35M / 7% turnover exposure if audited without remediation — "
            f"address critical gaps before enforcement dates."
        )
    return (
        "CRITICAL RISK: Readiness appears far below expectations — treat remediation as urgent "
        "and seek legal/compliance advice for your specific systems."
    )


def _estimate_hours(total_points: float, gap_count: int) -> int:
    base = 120 + (20 - total_points) * 12
    base += gap_count * 15
    return int(min(520, max(80, round(base))))


def _next_steps(gaps: list[str]) -> list[str]:
    steps = [
        "Create or validate an AI system inventory (Week 1)",
        "Classify systems against EU AI Act categories (Week 2–3)",
        "Stand up risk management & documentation for high-risk systems (Week 4–6)",
        "Complete technical documentation packs (Week 5–8)",
        "Plan conformity assessment / notified body route where required (Week 9–11)",
    ]
    if any("inventory" in g.lower() for g in gaps):
        steps[0] = "Prioritize: finalize AI system inventory with owners & data flows (Week 1)"
    if any("classified" in g.lower() or "categories" in g.lower() for g in gaps):
        steps[1] = "Prioritize: classification workshop + rationale log (Week 2–3)"
    return steps


def _validate_required(answers: dict[str, str | list[str]]) -> None:
    missing: list[str] = []
    for q in QUESTIONS_INTERNAL:
        if not _visible(q, answers):
            continue
        if q["id"] == "q8":
            q7 = answers.get("q7")
            if q7 == "no":
                continue
            if q7 == "yes":
                v = answers.get("q8")
                if not isinstance(v, list) or len(v) == 0:
                    missing.append("q8")
                continue
            continue
        val = answers.get(q["id"])
        if val is None or val == "" or val == []:
            missing.append(q["id"])
    if missing:
        raise HTTPException(status_code=400, detail={"missing": missing})


def _answers_labeled_for_email(
    answers: dict[str, str | list[str]],
) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for q in sorted(QUESTIONS_INTERNAL, key=lambda x: x["order"]):
        if not _visible(q, answers):
            continue
        if q["id"] == "q8" and answers.get("q7") == "no":
            continue
        raw = answers.get(q["id"])
        if q["type"] == "multi":
            if not isinstance(raw, list) or not raw:
                label = "—"
            else:
                selected = set(raw)
                labels = [o["label"] for o in q["options"] if o["value"] in selected]
                label = ", ".join(labels) if labels else "—"
        else:
            label = "—"
            if isinstance(raw, str):
                for o in q["options"]:
                    if o["value"] == raw:
                        label = o["label"]
                        break
        rows.append((q["text"], label))
    return rows


def _cors_extra_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "")
    return [o.strip() for o in raw.split(",") if o.strip()]


def _submission_meta(request: Request, body: AssessRequest) -> dict[str, Any]:
    """Non-answer context for admin review (CRM / attribution). Optional email still stored separately."""
    meta: dict[str, Any] = {}
    if body.contact_name:
        meta["contact_name"] = body.contact_name
    if body.company:
        meta["company"] = body.company
    if body.client_referrer:
        meta["client_referrer"] = body.client_referrer
    if body.page_url:
        meta["page_url"] = body.page_url
    if body.utm_source:
        meta["utm_source"] = body.utm_source
    if body.utm_medium:
        meta["utm_medium"] = body.utm_medium
    if body.utm_campaign:
        meta["utm_campaign"] = body.utm_campaign

    ref = request.headers.get("referer")
    if ref:
        meta["http_referer"] = ref[:2000]
    xff = request.headers.get("x-forwarded-for")
    if xff:
        first = xff.split(",")[0].strip()[:100]
        if first:
            meta["client_ip"] = first
    elif request.client and request.client.host:
        meta["client_ip"] = str(request.client.host)[:100]

    ua = request.headers.get("user-agent")
    if ua:
        meta["user_agent"] = ua[:500]

    return meta


def _admin_key_ok(x_admin_key: str | None) -> bool:
    expected = os.environ.get("ADMIN_API_KEY")
    return bool(expected and x_admin_key == expected)


def _admin_jwt_secret() -> str | None:
    return os.environ.get("ADMIN_JWT_SECRET") or os.environ.get("ADMIN_API_KEY")


def _parse_bearer(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    tok = authorization[7:].strip()
    return tok or None


def _admin_jwt_ok(token: str | None) -> bool:
    if not token:
        return False
    secret = _admin_jwt_secret()
    if not secret:
        return False
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload.get("scope") == "admin"
    except jwt.PyJWTError:
        return False


def _admin_password_ok(given: str, expected: str) -> bool:
    gb = given.encode("utf-8")
    eb = expected.encode("utf-8")
    if len(gb) != len(eb):
        return False
    return hmac.compare_digest(gb, eb)


def require_admin(
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
    authorization: str | None = Header(None),
) -> None:
    if _admin_key_ok(x_admin_key):
        return
    if _admin_jwt_ok(_parse_bearer(authorization)):
        return
    raise HTTPException(status_code=404, detail="Not found")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="EU AI Act Readiness Assessment",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_extra_origins(),
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/questions", response_model=list[QuestionOut])
def get_questions() -> list[QuestionOut]:
    out: list[QuestionOut] = []
    for q in sorted(QUESTIONS_INTERNAL, key=lambda x: x["order"]):
        opts = [OptionOut(value=o["value"], label=o["label"]) for o in q["options"]]
        out.append(
            QuestionOut(
                id=q["id"],
                section=q["section"],
                section_title=q["section_title"],
                order=q["order"],
                text=q["text"],
                type=q["type"],
                options=opts,
                show_if=q.get("show_if"),
            )
        )
    return out


@app.post("/api/assess", response_model=AssessResponse)
def assess(request: Request, body: AssessRequest) -> AssessResponse:
    if not body.consent:
        raise HTTPException(
            status_code=400,
            detail="Consent is required to submit. Please confirm storage of your responses.",
        )

    _validate_required(body.answers)
    total = _score_total(body.answers)
    score_percent = int(round((total / 20.0) * 100))
    band_key, band_label, band_summary = _band_from_points(total)
    gaps = _collect_gaps(body.answers)
    today = date.today()
    days_remaining = max(0, (EU_AI_ACT_DEADLINE - today).days)

    email_delivery: Literal["none", "sent", "failed", "misconfigured"] = "none"
    email_to = str(body.email) if body.email else None

    base = AssessResponse(
        score_points=round(total, 2),
        score_percent=score_percent,
        band=band_key,
        band_label=band_label,
        band_summary=band_summary,
        critical_gaps=gaps,
        risk_line=_risk_line(band_key, score_percent),
        days_remaining=days_remaining,
        deadline=EU_AI_ACT_DEADLINE.isoformat(),
        estimated_hours=_estimate_hours(total, len(gaps)),
        next_steps=_next_steps(gaps),
        calendly_url="https://calendly.com/beaconone-org/30min",
        website_url="https://beaconwatchtower.carrd.co",
        waitlist_url="https://docs.google.com/forms/d/e/1FAIpQLScOztY5nKDrlmnmUtHDd0fEN0qifiAxFcVcDBzc8BWmpkhj9A/viewform",
        submission_id=0,
        email_delivery="none",
    )
    report_for_db = base.model_dump()
    report_for_db.pop("submission_id", None)
    report_for_db.pop("email_delivery", None)

    answers_for_db: dict[str, Any] = dict(body.answers)
    sub_id = save_submission(
        email=email_to,
        answers=answers_for_db,
        report=report_for_db,
        consent=body.consent,
        meta=_submission_meta(request, body),
    )

    if email_to:
        html = build_report_html(
            answers_labeled=_answers_labeled_for_email(body.answers),
            report=report_for_db,
        )
        subject = "Your EU AI Act readiness report"
        if brevo_api_is_configured():
            try:
                send_report_via_brevo_api(
                    to_email=email_to, subject=subject, html=html
                )
                email_delivery = "sent"
            except Exception as exc:
                logger.exception("Report email (Brevo API) failed: %s", exc)
                email_delivery = "failed"
        elif smtp_is_configured():
            try:
                send_report_via_smtp(
                    to_email=email_to, subject=subject, html=html
                )
                email_delivery = "sent"
            except Exception as exc:
                logger.exception("Report email (SMTP) failed: %s", exc)
                email_delivery = "failed"
        elif os.environ.get("RESEND_API_KEY"):
            try:
                send_report_via_resend(
                    to_email=email_to, subject=subject, html=html
                )
                email_delivery = "sent"
            except Exception as exc:
                logger.exception("Report email (Resend) failed: %s", exc)
                email_delivery = "failed"
        else:
            email_delivery = "misconfigured"

    return base.model_copy(
        update={"submission_id": sub_id, "email_delivery": email_delivery}
    )


@app.post("/api/admin/login")
def admin_login(body: AdminLoginIn) -> dict[str, str]:
    """Email + password from env; returns JWT for Authorization: Bearer (8h)."""
    expected_email = (
        os.environ.get("ADMIN_EMAIL") or "beaconone.org@gmail.com"
    ).strip().lower()
    expected_pwd = os.environ.get("ADMIN_PASSWORD")
    if not expected_pwd:
        raise HTTPException(status_code=404, detail="Not found")
    if body.email.strip().lower() != expected_email:
        raise HTTPException(status_code=404, detail="Not found")
    if not _admin_password_ok(body.password, expected_pwd):
        raise HTTPException(status_code=404, detail="Not found")
    secret = _admin_jwt_secret()
    if not secret:
        raise HTTPException(
            status_code=500,
            detail="Set ADMIN_API_KEY or ADMIN_JWT_SECRET for admin tokens",
        )
    exp = datetime.now(timezone.utc) + timedelta(hours=8)
    token = jwt.encode(
        {"scope": "admin", "exp": exp},
        secret,
        algorithm="HS256",
    )
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/admin/submissions")
def admin_submissions(
    _auth: None = Depends(require_admin),
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    lim = max(1, min(limit, 200))
    off = max(0, offset)
    return list_submissions(limit=lim, offset=off)


@app.get("/api/admin/submissions/export")
def admin_submissions_export(
    _auth: None = Depends(require_admin),
) -> Response:
    """CSV for spreadsheets: includes flattened meta + full meta_json."""
    rows = list_submissions(limit=100_000, offset=0)
    buf = io.StringIO()
    fieldnames = [
        "id",
        "created_at",
        "email",
        "consent",
        "band",
        "score_percent",
        "contact_name",
        "company",
        "page_url",
        "client_referrer",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "client_ip",
        "http_referer",
        "user_agent",
        "meta_json",
    ]
    w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    for row in rows:
        meta = row.get("meta") or {}
        rep = row.get("report") or {}
        w.writerow(
            {
                "id": row["id"],
                "created_at": row.get("created_at") or "",
                "email": row.get("email") or "",
                "consent": row.get("consent", False),
                "band": rep.get("band", ""),
                "score_percent": rep.get("score_percent", ""),
                "contact_name": meta.get("contact_name", ""),
                "company": meta.get("company", ""),
                "page_url": meta.get("page_url", ""),
                "client_referrer": meta.get("client_referrer", ""),
                "utm_source": meta.get("utm_source", ""),
                "utm_medium": meta.get("utm_medium", ""),
                "utm_campaign": meta.get("utm_campaign", ""),
                "client_ip": meta.get("client_ip", ""),
                "http_referer": meta.get("http_referer", ""),
                "user_agent": meta.get("user_agent", ""),
                "meta_json": json.dumps(meta, ensure_ascii=False),
            }
        )
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="assessment_submissions.csv"'
        },
    )


@app.get("/api/admin/summary")
def admin_summary(_auth: None = Depends(require_admin)) -> dict[str, Any]:
    """Counts by band and email presence for quick analysis."""
    rows = admin_summary_rows()
    by_band: dict[str, int] = {}
    with_email = 0
    for r in rows:
        b = str(r.get("band") or "unknown")
        by_band[b] = by_band.get(b, 0) + 1
        if r.get("has_email"):
            with_email += 1
    n = len(rows)
    return {
        "total": n,
        "with_email": with_email,
        "without_email": n - with_email,
        "by_band": by_band,
        "submissions": rows,
    }


@app.get("/api/deadline")
def deadline_info() -> dict[str, Any]:
    today = date.today()
    return {
        "deadline": EU_AI_ACT_DEADLINE.isoformat(),
        "days_remaining": max(0, (EU_AI_ACT_DEADLINE - today).days),
        "as_of": today.isoformat(),
    }
