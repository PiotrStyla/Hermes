"""SMTP email sender for family reports.

Reads configuration from environment variables. If any required variable is
missing the sender logs a warning and returns without raising — existing call
pipelines must not break when email is not set up.

Supported providers
-------------------
- Gmail with App Password:
    SMTP_HOST=smtp.gmail.com  SMTP_PORT=587  SMTP_USER=you@gmail.com
    SMTP_PASSWORD=<16-char app password>  SMTP_FROM=you@gmail.com

- SendGrid SMTP relay:
    SMTP_HOST=smtp.sendgrid.net  SMTP_PORT=587  SMTP_USER=apikey
    SMTP_PASSWORD=<SendGrid API key>  SMTP_FROM=verified@yourdomain.com

- Any other STARTTLS SMTP server: same pattern.
"""

from __future__ import annotations

import logging
import os
import smtplib
import textwrap
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    host: str
    port: int
    user: str
    password: str
    from_addr: str

    @classmethod
    def from_env(cls) -> "EmailConfig | None":
        """Return config if all required vars are set, else None."""
        host = os.getenv("SMTP_HOST", "")
        port_str = os.getenv("SMTP_PORT", "587")
        user = os.getenv("SMTP_USER", "")
        password = os.getenv("SMTP_PASSWORD", "")
        from_addr = os.getenv("SMTP_FROM", user)

        if not all([host, user, password]):
            return None
        try:
            port = int(port_str)
        except ValueError:
            log.warning("SMTP_PORT=%r is not an integer, using 587.", port_str)
            port = 587
        return cls(host=host, port=port, user=user, password=password, from_addr=from_addr)

    def missing_keys(self) -> list[str]:
        missing = []
        if not self.host:
            missing.append("SMTP_HOST")
        if not self.user:
            missing.append("SMTP_USER")
        if not self.password:
            missing.append("SMTP_PASSWORD")
        return missing


def _markdown_to_html(md: str) -> str:
    """Minimal markdown → HTML (headers, bold, bullets). No deps required."""
    lines: list[str] = []
    in_ul = False
    for line in md.splitlines():
        stripped = line.strip()
        if stripped.startswith("### "):
            if in_ul:
                lines.append("</ul>"); in_ul = False
            lines.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("## "):
            if in_ul:
                lines.append("</ul>"); in_ul = False
            lines.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("# "):
            if in_ul:
                lines.append("</ul>"); in_ul = False
            lines.append(f"<h1>{stripped[2:]}</h1>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_ul:
                lines.append("<ul>"); in_ul = True
            item = stripped[2:]
            item = _bold(item)
            lines.append(f"  <li>{item}</li>")
        elif stripped == "---":
            if in_ul:
                lines.append("</ul>"); in_ul = False
            lines.append("<hr>")
        elif stripped == "":
            if in_ul:
                lines.append("</ul>"); in_ul = False
            lines.append("<br>")
        else:
            if in_ul:
                lines.append("</ul>"); in_ul = False
            lines.append(f"<p>{_bold(stripped)}</p>")
    if in_ul:
        lines.append("</ul>")
    body = "\n".join(lines)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: Georgia, serif; max-width: 640px; margin: 40px auto;
         color: #222; line-height: 1.6; padding: 0 20px; }}
  h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 8px; }}
  h2 {{ color: #34495e; margin-top: 24px; }}
  h3 {{ color: #555; }}
  hr {{ border: none; border-top: 1px solid #eee; margin: 24px 0; }}
  ul {{ padding-left: 20px; }}
  li {{ margin: 4px 0; }}
  p  {{ margin: 8px 0; }}
  .footer {{ font-size: 12px; color: #999; margin-top: 32px; }}
</style>
</head><body>
{body}
<p class="footer">Sent by Hermes Wellness Call Service.</p>
</body></html>"""


def _bold(text: str) -> str:
    import re
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


class EmailSender:
    """Send family reports via SMTP. No-op if not configured."""

    def __init__(self, config: EmailConfig | None = None):
        self.config = config or EmailConfig.from_env()

    def is_configured(self) -> bool:
        return self.config is not None

    def send_report(
        self,
        to_addr: str,
        senior_name: str,
        report_md: str,
        scores: dict[str, Any] | None = None,
    ) -> bool:
        """Send report to `to_addr`. Returns True on success, False on failure."""
        if not self.config:
            log.debug("Email not configured — skipping report for %s.", senior_name)
            return False
        if not to_addr:
            log.warning("No recipient address for %s — skipping email.", senior_name)
            return False

        subject = f"Wellness report — {senior_name}"
        if scores:
            avg = round(sum(v for v in scores.values() if isinstance(v, (int, float))) / len(scores), 1)
            subject += f" (avg score: {avg}/10)"

        html_body = _markdown_to_html(report_md)
        plain_body = textwrap.dedent(report_md)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.config.from_addr
        msg["To"] = to_addr
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.config.host, self.config.port, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(self.config.user, self.config.password)
                smtp.sendmail(self.config.from_addr, to_addr, msg.as_string())
            log.info("Report email sent to %s for %s.", to_addr, senior_name)
            return True
        except smtplib.SMTPAuthenticationError:
            log.error("SMTP auth failed — check SMTP_USER / SMTP_PASSWORD.")
        except smtplib.SMTPException as exc:
            log.error("SMTP error sending to %s: %s", to_addr, exc)
        except OSError as exc:
            log.error("Network error reaching %s:%s — %s", self.config.host, self.config.port, exc)
        return False
