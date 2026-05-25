"""Notifications module — outbound alerts after each call.

Currently supported:
- Email (SMTP): family report delivered as HTML email after finalize_call.

All senders are designed to be no-ops when not configured so existing
calls continue to work without any env vars set.
"""

from .email import EmailSender, EmailConfig

__all__ = ["EmailSender", "EmailConfig"]
