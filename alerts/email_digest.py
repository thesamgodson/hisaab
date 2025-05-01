"""Email digest sender for Hisaab accountability alerts.

Supports two delivery backends:
  1. Resend API (preferred) — env var HISAAB_RESEND_KEY
  2. SMTP fallback — env vars HISAAB_SMTP_HOST, HISAAB_SMTP_PORT,
     HISAAB_SMTP_USER, HISAAB_SMTP_PASSWORD, HISAAB_SMTP_FROM

Requires: resend>=2.0.0 for the Resend backend (optional dependency).
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graceful import of optional dependency
# ---------------------------------------------------------------------------

try:
    import resend as _resend_lib
    _RESEND_AVAILABLE = True
except ImportError:
    _RESEND_AVAILABLE = False

# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Hisaab Weekly Digest</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #f5f5f5;
      margin: 0;
      padding: 32px 16px;
      color: #1a1a1a;
    }}
    .container {{
      max-width: 640px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }}
    .header {{
      background: #1a1a2e;
      color: #ffffff;
      padding: 32px;
    }}
    .header h1 {{
      margin: 0 0 8px;
      font-size: 24px;
      font-weight: 700;
    }}
    .header p {{
      margin: 0;
      opacity: 0.7;
      font-size: 14px;
    }}
    .headline {{
      background: #eef2ff;
      border-left: 4px solid #4f46e5;
      padding: 16px 24px;
      margin: 24px;
      border-radius: 0 8px 8px 0;
      font-size: 15px;
      color: #3730a3;
      font-style: italic;
    }}
    .section {{
      padding: 0 24px 24px;
    }}
    .section h2 {{
      font-size: 16px;
      font-weight: 600;
      margin: 0 0 12px;
      color: #374151;
      border-bottom: 1px solid #e5e7eb;
      padding-bottom: 8px;
    }}
    .badge-bad  {{ color: #b91c1c; font-weight: 600; }}
    .badge-good {{ color: #15803d; font-weight: 600; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    td, th {{
      padding: 8px 12px;
      text-align: left;
      border-bottom: 1px solid #f3f4f6;
    }}
    th {{
      background: #f9fafb;
      font-weight: 600;
      font-size: 12px;
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .flag-chip {{
      display: inline-block;
      background: #fef2f2;
      color: #991b1b;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 12px;
      margin: 2px 2px 2px 0;
    }}
    .footer {{
      background: #f9fafb;
      padding: 20px 24px;
      font-size: 12px;
      color: #9ca3af;
      border-top: 1px solid #e5e7eb;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Hisaab Weekly Digest</h1>
      <p>Government Accountability Report &mdash; {generated_at}</p>
    </div>

    <div class="headline">{headline}</div>

    {degrading_section}
    {improving_section}
    {red_flags_section}

    <div class="footer">
      Hisaab tracks 11 Indian government welfare schemes. Data sourced from official portals.
      Generated at {generated_at_full} UTC.
    </div>
  </div>
</body>
</html>
"""

_DEGRADING_ROW = (
    "<tr>"
    "<td>{district}, {state}</td>"
    "<td>{scheme}</td>"
    "<td>{metric_name}</td>"
    "<td class='badge-bad'>{delta_pct:.1f}%</td>"
    "</tr>"
)

_IMPROVING_ROW = (
    "<tr>"
    "<td>{district}, {state}</td>"
    "<td>{scheme}</td>"
    "<td>{metric_name}</td>"
    "<td class='badge-good'>+{delta_pct:.1f}%</td>"
    "</tr>"
)

_RED_FLAG_ROW = (
    "<tr>"
    "<td>{district}, {state}</td>"
    "<td>{score:.0f}/100 ({grade})</td>"
    "<td>{flags_html}</td>"
    "</tr>"
)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _render_table_section(
    heading: str,
    headers: list[str],
    rows_html: list[str],
) -> str:
    if not rows_html:
        return ""
    header_cells = "".join(f"<th>{h}</th>" for h in headers)
    rows_combined = "\n".join(rows_html)
    return f"""
    <div class="section">
      <h2>{heading}</h2>
      <table>
        <thead><tr>{header_cells}</tr></thead>
        <tbody>{rows_combined}</tbody>
      </table>
    </div>
    """


def _render_html(digest: Any) -> str:
    """Convert a WeeklyDigest to a full HTML email string."""
    # Degrading section
    degrading_rows = [
        _DEGRADING_ROW.format(
            district=d.district,
            state=d.state,
            scheme=d.scheme,
            metric_name=d.metric_name,
            delta_pct=d.delta_pct,
        )
        for d in digest.top_degrading
    ]
    degrading_section = _render_table_section(
        f"Degrading Districts ({len(digest.top_degrading)})",
        ["District", "Scheme", "Metric", "Change"],
        degrading_rows,
    )

    # Improving section
    improving_rows = [
        _IMPROVING_ROW.format(
            district=d.district,
            state=d.state,
            scheme=d.scheme,
            metric_name=d.metric_name,
            delta_pct=d.delta_pct,
        )
        for d in digest.top_improving
    ]
    improving_section = _render_table_section(
        f"Improving Districts ({len(digest.top_improving)})",
        ["District", "Scheme", "Metric", "Change"],
        improving_rows,
    )

    # Red flags section
    red_flag_rows = [
        _RED_FLAG_ROW.format(
            district=e.district,
            state=e.state,
            score=e.score,
            grade=e.grade,
            flags_html="".join(f'<span class="flag-chip">{f}</span>' for f in e.flags[:3]),
        )
        for e in digest.new_red_flags[:10]
    ]
    red_flags_section = _render_table_section(
        f"Red Flag Districts ({len(digest.new_red_flags)})",
        ["District", "Score", "Issues"],
        red_flag_rows,
    )

    generated_at = digest.generated_at.strftime("%d %b %Y")
    generated_at_full = digest.generated_at.strftime("%Y-%m-%d %H:%M")

    return _HTML_TEMPLATE.format(
        headline=digest.headline,
        degrading_section=degrading_section,
        improving_section=improving_section,
        red_flags_section=red_flags_section,
        generated_at=generated_at,
        generated_at_full=generated_at_full,
    )


def _render_plaintext(digest: Any) -> str:
    """Convert a WeeklyDigest to a plain text email string."""
    lines = [
        "HISAAB WEEKLY DIGEST",
        "=" * 60,
        "",
        digest.headline,
        "",
    ]

    if digest.top_degrading:
        lines.append(f"DEGRADING DISTRICTS ({len(digest.top_degrading)})")
        lines.append("-" * 40)
        for d in digest.top_degrading:
            lines.append(
                f"  {d.district}, {d.state} — {d.scheme} {d.metric_name}: {d.delta_pct:.1f}%"
            )
        lines.append("")

    if digest.top_improving:
        lines.append(f"IMPROVING DISTRICTS ({len(digest.top_improving)})")
        lines.append("-" * 40)
        for d in digest.top_improving:
            lines.append(
                f"  {d.district}, {d.state} — {d.scheme} {d.metric_name}: +{d.delta_pct:.1f}%"
            )
        lines.append("")

    if digest.new_red_flags:
        lines.append(f"RED FLAG DISTRICTS ({len(digest.new_red_flags)})")
        lines.append("-" * 40)
        for e in digest.new_red_flags[:10]:
            flags_str = "; ".join(e.flags[:3])
            lines.append(f"  {e.district}, {e.state} ({e.score:.0f}/100 Grade {e.grade}) — {flags_str}")
        lines.append("")

    lines.append(
        f"Generated: {digest.generated_at.strftime('%Y-%m-%d %H:%M')} UTC | "
        "Hisaab — Government Accountability Infrastructure"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Delivery backends
# ---------------------------------------------------------------------------

def _send_via_resend(
    recipients: list[str],
    subject: str,
    html: str,
    plaintext: str,
    api_key: str,
) -> dict[str, Any]:
    """Send via the Resend API."""
    if not _RESEND_AVAILABLE:
        raise ImportError(
            "resend package is not installed. Install with: pip install resend>=2.0.0"
        )

    _resend_lib.api_key = api_key
    from_addr = os.environ.get("HISAAB_EMAIL_FROM", "alerts@hisaab.in")

    sent: list[str] = []
    failed: list[dict[str, str]] = []

    for recipient in recipients:
        try:
            _resend_lib.Emails.send(
                {
                    "from": from_addr,
                    "to": [recipient],
                    "subject": subject,
                    "html": html,
                    "text": plaintext,
                }
            )
            sent.append(recipient)
        except Exception as exc:
            logger.warning("Resend failed for %s: %s", recipient, exc)
            failed.append({"recipient": recipient, "error": str(exc)})

    return {"backend": "resend", "sent": sent, "failed": failed}


def _send_via_smtp(
    recipients: list[str],
    subject: str,
    html: str,
    plaintext: str,
) -> dict[str, Any]:
    """Send via SMTP using environment variable credentials."""
    host = os.environ.get("HISAAB_SMTP_HOST", "localhost")
    port = int(os.environ.get("HISAAB_SMTP_PORT", "587"))
    user = os.environ.get("HISAAB_SMTP_USER", "")
    password = os.environ.get("HISAAB_SMTP_PASSWORD", "")
    from_addr = os.environ.get("HISAAB_SMTP_FROM") or os.environ.get("HISAAB_EMAIL_FROM", "alerts@hisaab.in")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(plaintext, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    sent: list[str] = []
    failed: list[dict[str, str]] = []

    try:
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            if port != 25:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(from_addr, recipients, msg.as_string())
            sent = list(recipients)
    except Exception as exc:
        logger.error("SMTP delivery failed: %s", exc)
        failed = [{"recipient": r, "error": str(exc)} for r in recipients]

    return {"backend": "smtp", "sent": sent, "failed": failed}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_email_digest(
    recipients: list[str],
    digest: Any,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Send the weekly digest to a list of email addresses.

    Automatically selects the Resend backend if HISAAB_RESEND_KEY is set
    (or api_key is provided), otherwise falls back to SMTP.

    Args:
        recipients: List of recipient email addresses.
        digest: A WeeklyDigest instance.
        api_key: Optional Resend API key (overrides env var HISAAB_RESEND_KEY).

    Returns:
        dict with 'backend', 'sent', and 'failed' keys.
    """
    if not recipients:
        return {"backend": None, "sent": [], "failed": [], "error": "no_recipients"}

    resend_key = api_key or os.environ.get("HISAAB_RESEND_KEY")
    html = _render_html(digest)
    plaintext = _render_plaintext(digest)
    subject = f"Hisaab Weekly Digest — {digest.generated_at.strftime('%d %b %Y')}"

    if resend_key and _RESEND_AVAILABLE:
        return _send_via_resend(recipients, subject, html, plaintext, resend_key)

    logger.info("Resend not available or key not set — falling back to SMTP.")
    return _send_via_smtp(recipients, subject, html, plaintext)
