from __future__ import annotations

import json
import os
import re
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage
from html import escape
from typing import Any


def parse_sender_address(raw: str) -> tuple[str | None, str]:
    """Parse 'Name <email@domain>' or bare 'email@domain' -> (name|None, email)."""
    s = raw.strip()
    m = re.match(r"^(.+?)\s*<([^>]+@[^>]+)>\s*$", s)
    if m:
        name_part = m.group(1).strip()
        return (name_part or None, m.group(2).strip())
    if re.match(r"^[^\s<]+@[^\s>]+$", s):
        return (None, s)
    raise ValueError(f"Invalid sender address format: {raw!r}")


def brevo_api_is_configured() -> bool:
    if not os.environ.get("BREVO_API_KEY"):
        return False
    return bool(
        os.environ.get("BREVO_SENDER")
        or os.environ.get("SMTP_FROM")
        or os.environ.get("EMAIL_FROM")
    )


def send_report_via_brevo_api(*, to_email: str, subject: str, html: str) -> None:
    """
    Brevo transactional email over HTTPS (port 443).
    Use this on Render **free** tier: outbound SMTP ports 587/465 are blocked and will time out.
    Create an API key at https://app.brevo.com/settings/keys/api (not the SMTP key).
    """
    api_key = os.environ["BREVO_API_KEY"]
    raw_from = (
        os.environ.get("BREVO_SENDER")
        or os.environ.get("SMTP_FROM")
        or os.environ.get("EMAIL_FROM")
    )
    if not raw_from:
        raise RuntimeError("Set BREVO_SENDER or SMTP_FROM or EMAIL_FROM for Brevo sender")

    name, email_addr = parse_sender_address(raw_from)
    sender: dict[str, str] = {"email": email_addr}
    if name:
        sender["name"] = name

    payload = {
        "sender": sender,
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=data,
        headers={
            "accept": "application/json",
            "api-key": api_key,
            "Content-Type": "application/json",
            "User-Agent": "eu-ai-act-readiness-api/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            if resp.status not in (200, 201, 204):
                body = resp.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Brevo API error {resp.status}: {body}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Brevo API HTTP {e.code}: {body}") from e


def smtp_is_configured() -> bool:
    return bool(os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASSWORD"))


def send_report_via_smtp(*, to_email: str, subject: str, html: str) -> None:
    """
    Send HTML mail via SMTP.
    Note: Render **free** web services block outbound SMTP (25/465/587) — use Brevo HTTPS API instead.
    """
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    from_addr = (
        os.environ.get("SMTP_FROM") or os.environ.get("EMAIL_FROM") or user
    )
    use_ssl = os.environ.get("SMTP_SSL", "").lower() in ("1", "true", "yes")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(
        "Your EU AI Act readiness report is in HTML. "
        "Use an HTML-capable mail client to view the full report."
    )
    msg.add_alternative(html, subtype="html")

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=60) as server:
            server.login(user, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=60) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)


def build_report_html(
    *,
    answers_labeled: list[tuple[str, str]],
    report: dict[str, Any],
) -> str:
    gaps = report.get("critical_gaps") or []
    steps = report.get("next_steps") or []
    gaps_li = "".join(f"<li>{escape(str(g))}</li>" for g in gaps) or "<li>None flagged</li>"
    steps_li = "".join(f"<li>{escape(str(s))}</li>" for s in steps)

    qa_rows = "".join(
        f"<tr><td style='padding:8px;border:1px solid #e5e7eb;vertical-align:top'>{escape(q)}</td>"
        f"<td style='padding:8px;border:1px solid #e5e7eb'>{escape(a)}</td></tr>"
        for q, a in answers_labeled
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>EU AI Act readiness report</title></head>
<body style="font-family:system-ui,sans-serif;max-width:640px;margin:24px auto;color:#111827">
  <h1 style="font-size:20px">Your EU AI Act readiness report</h1>
  <p style="font-size:28px;font-weight:600">{escape(str(report.get("score_percent")))}%
    <span style="font-size:16px;font-weight:500;color:#4b5563"> — {escape(str(report.get("band_label")))}</span></p>
  <p style="color:#374151">{escape(str(report.get("band_summary")))}</p>
  <p><strong>Model score:</strong> {escape(str(report.get("score_points")))} / 20 weighted points</p>
  <h2 style="font-size:16px;margin-top:24px">Critical gaps</h2>
  <ul>{gaps_li}</ul>
  <h2 style="font-size:16px;margin-top:24px">Risk snapshot</h2>
  <p style="color:#374151">{escape(str(report.get("risk_line")))}</p>
  <p><strong>Days to deadline ({escape(str(report.get("deadline")))}):</strong>
    {escape(str(report.get("days_remaining")))}</p>
  <p><strong>Estimated remediation (indicative):</strong>
    {escape(str(report.get("estimated_hours")))} hours</p>
  <h2 style="font-size:16px;margin-top:24px">Recommended next steps</h2>
  <ol>{steps_li}</ol>
  <h2 style="font-size:16px;margin-top:24px">Your responses</h2>
  <table style="border-collapse:collapse;width:100%;font-size:14px">{qa_rows}</table>
  <p style="margin-top:24px;font-size:12px;color:#6b7280">This email is an automated summary for your
  records only and is not legal advice.</p>
</body></html>"""


# Resend only allows @vercel.app / random domains as From after you verify YOUR domain in DNS.
# For quick tests without a domain, use their documented sender (see Resend "Send Email" API docs).
_DEFAULT_RESEND_FROM = "EU AI Act Readiness <onboarding@resend.dev>"


def send_report_via_resend(*, to_email: str, subject: str, html: str) -> None:
    api_key = os.environ.get("RESEND_API_KEY")
    from_addr = (
        os.environ.get("EMAIL_FROM")
        or os.environ.get("RESEND_FROM")
        or _DEFAULT_RESEND_FROM
    )
    if not api_key:
        raise RuntimeError("RESEND_API_KEY must be set")

    payload = {
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # Resend / edge returns 403 error 1010 if User-Agent is missing (urllib omits it).
            "User-Agent": "eu-ai-act-readiness-api/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 201):
                body = resp.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Resend API error {resp.status}: {body}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend API HTTP {e.code}: {body}") from e
