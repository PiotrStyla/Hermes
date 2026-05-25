"""Tests for EmailSender and EmailConfig."""

from __future__ import annotations

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from src.notifications.email import EmailConfig, EmailSender, _markdown_to_html


# ---- EmailConfig ----

def test_config_from_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    assert EmailConfig.from_env() is None


def test_config_from_env_fully_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "test@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "abc123xyz456abcd")
    monkeypatch.setenv("SMTP_FROM", "test@gmail.com")
    cfg = EmailConfig.from_env()
    assert cfg is not None
    assert cfg.host == "smtp.gmail.com"
    assert cfg.port == 587
    assert cfg.user == "test@gmail.com"
    assert cfg.missing_keys() == []


def test_config_from_addr_defaults_to_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "sender@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "pass")
    monkeypatch.delenv("SMTP_FROM", raising=False)
    cfg = EmailConfig.from_env()
    assert cfg is not None
    assert cfg.from_addr == "sender@example.com"


def test_config_invalid_port_falls_back_to_587(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "not-a-number")
    monkeypatch.setenv("SMTP_USER", "u@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "pass")
    cfg = EmailConfig.from_env()
    assert cfg is not None
    assert cfg.port == 587


# ---- EmailSender.is_configured ----

def test_sender_not_configured_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    assert not EmailSender().is_configured()


def test_sender_configured_with_explicit_config() -> None:
    cfg = EmailConfig("smtp.gmail.com", 587, "u@g.com", "pass", "u@g.com")
    assert EmailSender(config=cfg).is_configured()


# ---- EmailSender.send_report — no-op cases ----

def test_send_no_config_returns_false() -> None:
    sender = EmailSender(config=None)
    result = sender.send_report("family@example.com", "Alice", "# Report\nAll good.")
    assert result is False


def test_send_empty_to_addr_returns_false() -> None:
    cfg = EmailConfig("smtp.gmail.com", 587, "u@g.com", "pass", "u@g.com")
    result = EmailSender(config=cfg).send_report("", "Alice", "# Report")
    assert result is False


# ---- EmailSender.send_report — success via mock ----

def _make_sender() -> EmailSender:
    return EmailSender(config=EmailConfig("smtp.gmail.com", 587, "u@g.com", "pass", "u@g.com"))


def test_send_report_success() -> None:
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)
    with patch("smtplib.SMTP", return_value=mock_smtp):
        result = _make_sender().send_report(
            "family@example.com", "Alice",
            "# Daily Report\n\nAlice is well today.",
            scores={"warmth": 8, "listening": 7},
        )
    assert result is True
    mock_smtp.sendmail.assert_called_once()
    call_args = mock_smtp.sendmail.call_args
    assert call_args[0][1] == "family@example.com"


def test_send_report_subject_includes_name_and_avg() -> None:
    import email as email_lib
    import email.header as email_header

    captured = {}
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=False)

    def capture_sendmail(from_addr, to_addr, msg_str):
        captured["msg"] = msg_str

    mock_smtp.sendmail.side_effect = capture_sendmail
    with patch("smtplib.SMTP", return_value=mock_smtp):
        _make_sender().send_report(
            "x@x.com", "Jadwiga", "Report",
            scores={"warmth": 8, "listening": 8, "info_quality": 8, "brevity": 8},
        )
    msg = email_lib.message_from_string(captured["msg"])
    decoded_parts = email_header.decode_header(msg["Subject"])
    subject = "".join(
        part.decode(enc or "utf-8") if isinstance(part, bytes) else part
        for part, enc in decoded_parts
    )
    assert "Jadwiga" in subject
    assert "8.0/10" in subject


# ---- Auth failure handled gracefully ----

def test_auth_failure_returns_false() -> None:
    with patch("smtplib.SMTP") as mock_cls:
        instance = MagicMock()
        instance.__enter__ = MagicMock(return_value=instance)
        instance.__exit__ = MagicMock(return_value=False)
        instance.starttls = MagicMock()
        instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")
        mock_cls.return_value = instance
        result = _make_sender().send_report("x@x.com", "Alice", "Report")
    assert result is False


# ---- _markdown_to_html ----

def test_html_contains_h1() -> None:
    html = _markdown_to_html("# Daily Report\n\nAll good.")
    assert "<h1>Daily Report</h1>" in html


def test_html_contains_h2() -> None:
    html = _markdown_to_html("## Health\n\nFine.")
    assert "<h2>Health</h2>" in html


def test_html_renders_bold() -> None:
    html = _markdown_to_html("This is **important**.")
    assert "<strong>important</strong>" in html


def test_html_renders_bullets() -> None:
    html = _markdown_to_html("- Item one\n- Item two")
    assert "<ul>" in html
    assert "<li>Item one</li>" in html


def test_html_renders_hr() -> None:
    html = _markdown_to_html("---")
    assert "<hr>" in html


def test_html_is_valid_structure() -> None:
    html = _markdown_to_html("# Title\n\n## Section\n\n- point")
    assert "<!DOCTYPE html>" in html
    assert "</html>" in html
