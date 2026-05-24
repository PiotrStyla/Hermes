"""Lightweight PII redaction for outbound artifacts (family reports, etc.).

Deliberately conservative regex set — false positives are fine here, missed PII
is not. We redact:
- email addresses
- phone numbers (Polish & international forms)
- PESEL (Polish national ID, 11 digits)
- IBAN (PL + generic)
- street addresses with house number patterns

For more nuanced PII (medication names, diagnosis specifics) we rely on the
Operator's prompt and the Supervisor's review, not regex.
"""

from __future__ import annotations

import re

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3}[\s-]?\d{2,4}[\s-]?\d{2,4}(?!\d)"
)
_PESEL = re.compile(r"(?<!\d)\d{11}(?!\d)")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
# Polish-style street with house number: "ul. Kwiatowa 12/3", "Aleja Niepodległości 47"
_STREET = re.compile(
    r"\b(?:ul\.?|ulica|al\.?|aleja|os\.?|osiedle|pl\.?|plac)\s+[A-ZŚŹŻĄĘÓŁŃĆ][\wŚŹŻĄĘÓŁŃĆśźżąęółńć -]{2,40}\s+\d+[A-Za-z]?(?:/\d+)?",
    re.IGNORECASE,
)


def redact_pii(text: str) -> str:
    """Replace recognised PII spans with `[REDACTED-<kind>]`.

    Order matters: PESEL/IBAN must run before generic phone numbers because
    those patterns are subsets digit-wise.
    """
    if not text:
        return text
    text = _IBAN.sub("[REDACTED-IBAN]", text)
    text = _PESEL.sub("[REDACTED-PESEL]", text)
    text = _EMAIL.sub("[REDACTED-EMAIL]", text)
    text = _PHONE.sub("[REDACTED-PHONE]", text)
    text = _STREET.sub("[REDACTED-ADDRESS]", text)
    return text
