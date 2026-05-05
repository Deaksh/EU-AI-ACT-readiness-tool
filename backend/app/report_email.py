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


def _email_band_theme(band: str) -> dict[str, str]:
    """Inline styles approximating the on-screen readiness cards (email-safe)."""
    b = (band or "orange").lower().strip()
    themes: dict[str, dict[str, str]] = {
        "green": {
            "hero_bg": "#ecfdf5",
            "hero_border": "#6ee7b7",
            "pill_bg": "#059669",
            "pill_color": "#ffffff",
            "bar": "linear-gradient(90deg,#34d399,#0d9488)",
            "subcard_bg": "#f0fdf4",
            "subcard_border": "#bbf7d0",
        },
        "yellow": {
            "hero_bg": "#fffbeb",
            "hero_border": "#fcd34d",
            "pill_bg": "#d97706",
            "pill_color": "#ffffff",
            "bar": "linear-gradient(90deg,#fbbf24,#ca8a04)",
            "subcard_bg": "#fffbeb",
            "subcard_border": "#fde68a",
        },
        "orange": {
            "hero_bg": "#fff7ed",
            "hero_border": "#fdba74",
            "pill_bg": "#ea580c",
            "pill_color": "#ffffff",
            "bar": "linear-gradient(90deg,#fb923c,#c2410c)",
            "subcard_bg": "#fff7ed",
            "subcard_border": "#fed7aa",
        },
        "red": {
            "hero_bg": "#fff1f2",
            "hero_border": "#fda4af",
            "pill_bg": "#e11d48",
            "pill_color": "#ffffff",
            "bar": "linear-gradient(90deg,#fb7185,#b91c1c)",
            "subcard_bg": "#fff1f2",
            "subcard_border": "#fecdd3",
        },
    }
    return themes.get(b, themes["orange"])


def _band_short_label(band_label: object) -> str:
    raw = str(band_label or "").strip()
    if "—" in raw:
        tail = raw.split("—", 1)[1].strip()
        if tail:
            return escape(tail)
    return escape(raw) if raw else "—"


def build_report_html(
    *,
    answers_labeled: list[tuple[str, str]],
    report: dict[str, Any],
) -> str:
    gaps = report.get("critical_gaps") or []
    steps = report.get("next_steps") or []
    gaps_li = "".join(
        f"<li style='margin:0 0 8px 0;padding-left:4px'><span style='color:#f43f5e;margin-right:6px'>✕</span>{escape(str(g))}</li>"
        for g in gaps
    ) or "<li style='color:#6b7280'>None flagged</li>"
    steps_li = "".join(f"<li style='margin:0 0 8px 0'>{escape(str(s))}</li>" for s in steps)

    qa_rows = "".join(
        f"<tr><td style='padding:10px 12px;border:1px solid #e5e7eb;vertical-align:top;color:#374151;font-size:14px'>{escape(q)}</td>"
        f"<td style='padding:10px 12px;border:1px solid #e5e7eb;color:#111827;font-size:14px'>{escape(a)}</td></tr>"
        for q, a in answers_labeled
    )

    band = str(report.get("band") or "orange")
    t = _email_band_theme(band)
    pct_raw = report.get("score_percent")
    try:
        pct = max(0, min(100, int(pct_raw)))
    except (TypeError, ValueError):
        pct = 0

    pct_disp = escape(str(pct_raw if pct_raw is not None else "—"))
    pill = _band_short_label(report.get("band_label"))

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="color-scheme" content="light"><title>EU AI Act readiness report</title></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#111827">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:24px 16px">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px">
        <tr><td style="background:{t["hero_bg"]};border:1px solid {t["hero_border"]};border-radius:16px;padding:28px 24px 24px">
          <p style="margin:0 0 6px;font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#6b7280">Your EU AI Act readiness</p>
          <p style="margin:0 0 12px;font-size:34px;font-weight:700;line-height:1.15;color:#111827">
            {pct_disp}%<span style="display:inline-block;vertical-align:middle;margin-left:10px;padding:6px 14px;border-radius:999px;font-size:13px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;background:{t["pill_bg"]};color:{t["pill_color"]}">{pill}</span>
          </p>
          <p style="margin:0 0 18px;font-size:15px;line-height:1.55;color:#374151">{escape(str(report.get("band_summary") or ""))}</p>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td>
            <div style="height:10px;border-radius:999px;background:#e5e7eb;overflow:hidden">
              <div style="height:10px;width:{pct}%;border-radius:999px;background:{t["bar"]}"></div>
            </div>
            <p style="margin:10px 0 0;font-size:12px;color:#6b7280">Model score: <strong style="color:#374151">{escape(str(report.get("score_points")))}</strong> / 20 weighted points</p>
          </td></tr></table>
        </td></tr>
        <tr><td height="16"></td></tr>
        <tr><td>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:separate;border-spacing:0 12px">
            <tr>
              <td width="48%" valign="top" style="background:{t["subcard_bg"]};border:1px solid {t["subcard_border"]};border-radius:14px;padding:18px 16px">
                <p style="margin:0 0 10px;font-size:13px;font-weight:600;color:#111827">Critical gaps</p>
                <ul style="margin:0;padding-left:18px;color:#374151;font-size:14px;line-height:1.45">{gaps_li}</ul>
              </td>
              <td width="4%"></td>
              <td width="48%" valign="top" style="background:{t["subcard_bg"]};border:1px solid {t["subcard_border"]};border-radius:14px;padding:18px 16px">
                <p style="margin:0 0 10px;font-size:13px;font-weight:600;color:#111827">Risk snapshot</p>
                <p style="margin:0 0 12px;font-size:14px;line-height:1.5;color:#374151">{escape(str(report.get("risk_line") or ""))}</p>
                <p style="margin:0 0 6px;font-size:13px;color:#374151"><strong>Deadline</strong> ({escape(str(report.get("deadline")))}): <strong>{escape(str(report.get("days_remaining")))}</strong> days</p>
                <p style="margin:0;font-size:13px;color:#374151"><strong>Est. remediation:</strong> {escape(str(report.get("estimated_hours")))} hours</p>
              </td>
            </tr>
          </table>
        </td></tr>
        <tr><td style="background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;padding:20px 18px;margin-top:4px">
          <p style="margin:0 0 12px;font-size:13px;font-weight:600;color:#111827">Recommended next steps</p>
          <ol style="margin:0;padding-left:20px;color:#374151;font-size:14px;line-height:1.5">{steps_li}</ol>
        </td></tr>
        <tr><td height="12"></td></tr>
        <tr><td style="background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;padding:20px 18px">
          <p style="margin:0 0 12px;font-size:13px;font-weight:600;color:#111827">Your responses</p>
          <table style="border-collapse:collapse;width:100%">{qa_rows}</table>
        </td></tr>
        <tr><td style="padding:20px 8px 8px;text-align:center;font-size:12px;color:#6b7280;line-height:1.45">This email is an automated summary for your records only and is not legal advice.</td></tr>
      </table>
    </td></tr>
  </table>
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
