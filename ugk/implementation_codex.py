"""Reader for the root IMPLEMENTATION_CODEX.md navigation artifact.

This module is intentionally pure and read-only. The implementation codex is a
human-authored navigation surface, not law and not the generated CODEX.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def codex_path(root: Path | None = None) -> Path:
    return (root or root_dir()) / "IMPLEMENTATION_CODEX.md"


def load_entries(root: Path | None = None) -> dict[str, dict]:
    path = codex_path(root)
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    entries: dict[str, dict] = {}
    for match in re.finditer(r"```json\s*(.*?)\s*```", text, re.DOTALL):
        obj = json.loads(match.group(1))
        cid = obj.get("concept_id")
        if isinstance(cid, str) and cid:
            entries[cid] = obj
    return entries


__all__ = ["codex_path", "load_entries", "root_dir"]
