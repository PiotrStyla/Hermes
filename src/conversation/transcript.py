"""Transcript formatting utilities."""

from __future__ import annotations

from datetime import datetime


END_TOKEN = "<<END_CALL>>"


def strip_end_token(text: str) -> str:
    return text.replace(END_TOKEN, "").rstrip()


def has_end_token(text: str) -> bool:
    return END_TOKEN in text


def format_transcript(senior_name: str, history: list[dict[str, str]]) -> str:
    """Render the conversation history as a markdown transcript."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: list[str] = [
        f"# Call Transcript — {senior_name}",
        "",
        f"_Recorded {timestamp}_",
        "",
    ]
    for turn in history:
        speaker = "Operator" if turn["role"] == "operator" else senior_name
        content = strip_end_token(turn["content"]).strip()
        lines.append(f"**{speaker}:** {content}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
