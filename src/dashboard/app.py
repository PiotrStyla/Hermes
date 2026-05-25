"""FastAPI dashboard application."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..compliance.consent import ConsentStore
from ..compliance.review_queue import ReviewQueue
from ..scheduling.store import ScheduleStore
from ..seniors.store import SeniorStore


_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _score_avg(scores: dict) -> float:
    vals = [v for v in scores.values() if isinstance(v, (int, float))]
    return round(sum(vals) / len(vals), 1) if vals else 0.0


def _senior_summaries() -> list[dict[str, Any]]:
    store = SeniorStore()
    consent_store = ConsentStore()
    sched_store = ScheduleStore()
    summaries = []
    for sid in store.list_ids():
        if not store.exists(sid):
            continue
        try:
            profile = store.load(sid)
        except Exception:
            continue
        records = store.list_call_records(sid)
        last = records[-1] if records else None
        consent = consent_store.load(sid)
        sched = None
        if sched_store.exists(sid):
            try:
                sched = sched_store.load(sid)
            except Exception:
                pass
        summaries.append({
            "id": sid,
            "name": profile.name,
            "age": profile.age,
            "language": profile.language,
            "call_count": len(records),
            "last_call": last["date"][:10] if last else None,
            "last_scores": last["scores"] if last else {},
            "last_avg": _score_avg(last["scores"]) if last else None,
            "consent_status": consent.status.value,
            "schedule": sched.summary() if sched else None,
        })
    return summaries


def create_app() -> FastAPI:
    app = FastAPI(title="Hermes Dashboard", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> Response:
        summaries = _senior_summaries()
        pending = len(ReviewQueue().list(status="pending"))
        return templates.TemplateResponse("home.html", {
            "request": request,
            "seniors": summaries,
            "pending_review": pending,
        })

    @app.get("/seniors/{senior_id}", response_class=HTMLResponse)
    async def senior_detail(request: Request, senior_id: str) -> Response:
        store = SeniorStore()
        if not store.exists(senior_id):
            return HTMLResponse("<h1>Senior not found</h1>", status_code=404)
        profile = store.load(senior_id)
        records = store.list_call_records(senior_id)
        consent = ConsentStore().load(senior_id)
        sched = None
        sched_store = ScheduleStore()
        if sched_store.exists(senior_id):
            try:
                sched = sched_store.load(senior_id)
            except Exception:
                pass
        reports = [
            {"name": p.name, "path": str(p)}
            for p in reversed(store.list_reports(senior_id))
        ]
        chart_labels = [r["date"][:10] for r in records]
        axes = ["warmth", "listening", "info_quality", "brevity"]
        chart_datasets = {
            ax: [r["scores"].get(ax) for r in records]
            for ax in axes
        }
        return templates.TemplateResponse("senior.html", {
            "request": request,
            "profile": profile,
            "records": records,
            "consent": consent,
            "schedule": sched,
            "reports": reports,
            "chart_labels": json.dumps(chart_labels),
            "chart_datasets": json.dumps(chart_datasets),
        })

    @app.get("/review", response_class=HTMLResponse)
    async def review(request: Request, status: str = "pending") -> Response:
        rq = ReviewQueue()
        entries = rq.list(status=status if status != "all" else None)
        return templates.TemplateResponse("review.html", {
            "request": request,
            "entries": entries,
            "current_status": status,
        })

    @app.post("/review/{entry_id}/decide", response_class=HTMLResponse)
    async def decide(
        request: Request,
        entry_id: str,
        action: str = Form(...),
        comment: str = Form(""),
    ) -> Response:
        rq = ReviewQueue()
        try:
            entry = rq.decide(entry_id, status=action, decided_by="dashboard", comment=comment)
        except (ValueError, FileNotFoundError) as exc:
            return HTMLResponse(f'<span class="text-red-500">{exc}</span>')
        badge_class = "bg-green-100 text-green-800" if action == "approved" else "bg-red-100 text-red-800"
        return HTMLResponse(
            f'<span class="px-2 py-1 rounded text-xs font-semibold {badge_class}">'
            f'{action.upper()}</span>'
        )

    @app.get("/schedule", response_class=HTMLResponse)
    async def schedule(request: Request) -> Response:
        schedules = ScheduleStore().list_all()
        return templates.TemplateResponse("schedule.html", {
            "request": request,
            "schedules": schedules,
        })

    return app
