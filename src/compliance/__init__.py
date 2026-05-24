"""Compliance primitives: consent, retention, audit log, PII redaction.

These are deterministic safeguards (code, not LLM judgement) that any caller of
the system must respect before recording or transmitting senior data.

A `ComplianceReviewerAgent` lives in `reviewer.py` and is LLM-backed — it is an
*advisor* over artifacts (prompts, reports), never an enforcer of legal rules.
"""

from .audit import AuditLog
from .consent import ConsentRecord, ConsentStore, ConsentStatus
from .redaction import redact_pii
from .retention import RetentionPolicy, RetentionStore
from .reviewer import ComplianceReviewerAgent

__all__ = [
    "AuditLog",
    "ComplianceReviewerAgent",
    "ConsentRecord",
    "ConsentStore",
    "ConsentStatus",
    "RetentionPolicy",
    "RetentionStore",
    "redact_pii",
]
