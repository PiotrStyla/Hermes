"""Family dashboard — FastAPI web UI for Hermes.

Run with:  hermes dashboard [--host 0.0.0.0] [--port 8080]

Pages
-----
GET /              — home: list of all seniors with last-call summary
GET /seniors/{id}  — senior detail: profile, score history chart, reports
GET /review        — human review queue (HTMX approve / flag)
GET /schedule      — call schedule overview
"""

from .app import create_app

__all__ = ["create_app"]
