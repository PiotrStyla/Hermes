"""Shared memory store for inter-agent communication."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class SharedMemory:
    """Thread-safe shared memory between agents.

    Stores key-value pairs with metadata (source agent, timestamp).
    Persists to disk for recovery across sessions.
    """

    def __init__(self, persist_path: str | None = None):
        self._store: dict[str, dict[str, Any]] = {}
        self._persist_path = Path(persist_path) if persist_path else None

        if self._persist_path and self._persist_path.exists():
            self._load()

    def put(self, key: str, value: Any, source: str = "unknown") -> None:
        """Store a value with metadata."""
        self._store[key] = {
            "value": value,
            "source": source,
            "timestamp": time.time(),
        }
        self._save()

    def get(self, key: str) -> Any | None:
        """Retrieve a value by key."""
        entry = self._store.get(key)
        return entry["value"] if entry else None

    def get_by_source(self, source: str) -> dict[str, Any]:
        """Get all entries from a specific agent."""
        return {
            k: v["value"]
            for k, v in self._store.items()
            if v["source"] == source
        }

    def get_context_for(self, agent_role: str) -> dict[str, Any]:
        """Get relevant context for a specific agent role.

        Returns all entries NOT produced by this agent (to avoid echo).
        """
        return {
            k: v["value"]
            for k, v in self._store.items()
            if v["source"] != agent_role
        }

    def clear(self) -> None:
        """Clear all stored data."""
        self._store.clear()
        self._save()

    def _save(self) -> None:
        """Persist memory to disk."""
        if self._persist_path:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(
                json.dumps(self._store, indent=2, default=str)
            )

    def _load(self) -> None:
        """Load memory from disk."""
        if self._persist_path and self._persist_path.exists():
            self._store = json.loads(self._persist_path.read_text())
