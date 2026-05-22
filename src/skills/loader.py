"""Loads operator skills from `data/skills/operator/`."""

from __future__ import annotations

from pathlib import Path


SKILLS_DIR = Path(__file__).resolve().parents[2] / "data" / "skills" / "operator"


class SkillsLoader:
    """Reads markdown skill files and assembles them for the operator's prompt."""

    def __init__(self, skills_dir: Path = SKILLS_DIR):
        self.skills_dir = skills_dir

    def load_all(self) -> dict[str, str]:
        """Return {skill_name: content} for every non-underscore .md in skills_dir."""
        if not self.skills_dir.exists():
            return {}
        skills: dict[str, str] = {}
        for path in sorted(self.skills_dir.glob("*.md")):
            if path.name.startswith("_"):
                continue
            skills[path.stem] = path.read_text(encoding="utf-8")
        return skills

    def load_index(self) -> str:
        index = self.skills_dir / "_index.md"
        return index.read_text(encoding="utf-8") if index.exists() else ""

    def assemble_prompt_section(self) -> str:
        """Concatenate all skills into a single block for the operator's system prompt."""
        skills = self.load_all()
        if not skills:
            return "(no skills available)"
        parts = [self.load_index().strip(), ""]
        for name, content in skills.items():
            parts.append(f"---\n\n{content.strip()}")
        return "\n\n".join(p for p in parts if p)

    def get(self, skill_name: str) -> str | None:
        path = self.skills_dir / f"{skill_name}.md"
        return path.read_text(encoding="utf-8") if path.exists() else None
