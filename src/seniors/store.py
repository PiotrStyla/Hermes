"""Senior profile and per-senior data store.

Each senior lives in `data/seniors/<senior-id>/` with:
- profile.json
- transcripts/<timestamp>.md
- reports/<timestamp>.md
- learnings/notes.md

The persona file lives in `data/personas/<senior-id>.md`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SENIORS_DIR = DATA_DIR / "seniors"
PERSONAS_DIR = DATA_DIR / "personas"


@dataclass
class SeniorProfile:
    """In-memory representation of a senior's profile."""

    id: str
    name: str
    age: int
    language: str
    conditions: list[str]
    medications: list[str]
    preferences: dict[str, Any]
    family_contact: dict[str, str]
    notes: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SeniorProfile":
        return cls(
            id=data["id"],
            name=data["name"],
            age=data["age"],
            language=data.get("language", "en"),
            conditions=data.get("conditions", []),
            medications=data.get("medications", []),
            preferences=data.get("preferences", {}),
            family_contact=data.get("family_contact", {}),
            notes=data.get("notes", ""),
        )

    def to_summary(self) -> str:
        """Return a concise human-readable summary used in agent prompts."""
        prefs = self.preferences or {}
        loved = ", ".join(prefs.get("topics_loved", []))
        avoid = ", ".join(prefs.get("topics_avoid", []))
        meds = ", ".join(self.medications) if self.medications else "none on file"
        conditions = ", ".join(self.conditions) if self.conditions else "none on file"
        return (
            f"Name: {self.name}\n"
            f"Age: {self.age}\n"
            f"Language: {self.language}\n"
            f"Known conditions: {conditions}\n"
            f"Medications: {meds}\n"
            f"Tone preference: {prefs.get('tone', 'warm and friendly')}\n"
            f"Topics they love: {loved or '(none recorded)'}\n"
            f"Topics to avoid: {avoid or '(none)'}\n"
            f"Family contact: {self.family_contact.get('name', '')} <{self.family_contact.get('email', '')}>\n"
            f"Notes: {self.notes}"
        )


class SeniorStore:
    """Filesystem CRUD for seniors."""

    def __init__(self, base_dir: Path = SENIORS_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        PERSONAS_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Discovery ----

    def list_ids(self) -> list[str]:
        return sorted(p.name for p in self.base_dir.iterdir() if p.is_dir())

    def exists(self, senior_id: str) -> bool:
        return (self.base_dir / senior_id / "profile.json").exists()

    # ---- Read ----

    def load(self, senior_id: str) -> SeniorProfile:
        path = self.base_dir / senior_id / "profile.json"
        if not path.exists():
            raise FileNotFoundError(f"Senior {senior_id!r} not found at {path}")
        return SeniorProfile.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def load_persona(self, senior_id: str) -> str:
        path = PERSONAS_DIR / f"{senior_id}.md"
        if not path.exists():
            raise FileNotFoundError(f"Persona for {senior_id!r} not found at {path}")
        return path.read_text(encoding="utf-8")

    def load_learnings(self, senior_id: str) -> str:
        path = self.base_dir / senior_id / "learnings" / "notes.md"
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    # ---- Write ----

    def save_transcript(self, senior_id: str, content: str) -> Path:
        return self._save_timestamped(senior_id, "transcripts", content)

    def save_report(self, senior_id: str, content: str) -> Path:
        return self._save_timestamped(senior_id, "reports", content)

    def append_learning(self, senior_id: str, note: str) -> None:
        path = self.base_dir / senior_id / "learnings" / "notes.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        path.write_text(
            existing.rstrip() + f"\n\n## {timestamp}\n\n{note.strip()}\n",
            encoding="utf-8",
        )

    def list_transcripts(self, senior_id: str) -> list[Path]:
        d = self.base_dir / senior_id / "transcripts"
        return sorted(d.glob("*.md")) if d.exists() else []

    def list_reports(self, senior_id: str) -> list[Path]:
        d = self.base_dir / senior_id / "reports"
        return sorted(d.glob("*.md")) if d.exists() else []

    # ---- Internal ----

    def _save_timestamped(self, senior_id: str, subdir: str, content: str) -> Path:
        d = self.base_dir / senior_id / subdir
        d.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        path = d / f"{timestamp}.md"
        path.write_text(content, encoding="utf-8")
        return path
