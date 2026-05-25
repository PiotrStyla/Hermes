"""Mid-call consent withdrawal detection.

RODO Art. 7(3) requires that the data subject be able to withdraw consent at
any time, as easily as they gave it. We detect a small set of explicit
withdrawal phrases in the senior's transcribed speech and trigger a graceful
end-of-call + revoke on the consent record.

This is intentionally a small, deterministic regex layer. The Operator's
prompt also instructs it to honour withdrawal, but we don't rely on the LLM
for legal-grade enforcement.
"""

from __future__ import annotations

import re

# Patterns are matched case-insensitively against the transcribed senior
# utterance. We use word-boundary-ish anchors so common nearby vocabulary
# (e.g. "stopa" in Polish = "foot") doesn't false-positive.
_PATTERNS = [
    # English
    re.compile(r"\bi\s+withdraw(?:\s+my)?\s+consent\b", re.IGNORECASE),
    re.compile(r"\bdon'?t\s+call\s+(?:me\s+)?again\b", re.IGNORECASE),
    re.compile(r"\bstop\s+calling\b", re.IGNORECASE),
    re.compile(r"\bremove\s+me\b", re.IGNORECASE),
    re.compile(r"\bi\s+want\s+to\s+end\s+(?:this|the)\s+call\b", re.IGNORECASE),
    # Polish
    re.compile(r"\bwycofuj[eę]\s+(?:moj[ąa]\s+)?zgod[eę]\b", re.IGNORECASE),
    re.compile(r"\bnie\s+zgadzam\s+si[eę]\b", re.IGNORECASE),
    re.compile(r"\b(?:prosz[eę]\s+)?nie\s+dzwoni[ćc]\s+(?:do\s+mnie\s+)?wi[eę]cej\b", re.IGNORECASE),
    re.compile(r"\bkoniec\s+rozmowy\b", re.IGNORECASE),
    re.compile(r"\brozłącz(?:am)?\s+si[eę]\b", re.IGNORECASE),
    re.compile(r"\bnie\s+chc[eę]\s+(?:tej\s+)?rozmowy\b", re.IGNORECASE),
    re.compile(r"\bprosz[eę]\s+nie\s+nagrywa[ćc]\b", re.IGNORECASE),
]


def is_withdrawal(text: str) -> bool:
    """Return True if `text` looks like the senior is withdrawing consent."""
    if not text:
        return False
    return any(p.search(text) for p in _PATTERNS)
