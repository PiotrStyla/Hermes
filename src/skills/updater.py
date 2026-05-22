"""Versions and updates operator skill files based on Supervisor feedback."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from .loader import SKILLS_DIR


VERSIONS_DIR = SKILLS_DIR / "_versions"


class SkillsUpdater:
    """Versions an existing skill before overwriting it with an updated version."""

    def __init__(self, skills_dir: Path = SKILLS_DIR):
        self.skills_dir = skills_dir
        self.versions_dir = self.skills_dir / "_versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)

    def update(self, skill_name: str, new_content: str) -> Path:
        """Snapshot the existing skill (if any) and write the new content.

        Returns the path to the updated skill file.
        """
        target = self.skills_dir / f"{skill_name}.md"

        if target.exists():
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            backup = self.versions_dir / f"{timestamp}_{skill_name}.md"
            shutil.copy2(target, backup)

        target.write_text(new_content.rstrip() + "\n", encoding="utf-8")
        return target
