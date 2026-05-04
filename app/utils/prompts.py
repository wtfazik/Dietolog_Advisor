from __future__ import annotations

from pathlib import Path

from app.config import get_settings


def load_prompt(name: str) -> str:
    settings = get_settings()
    path = Path(settings.prompts_dir) / f"{name}.txt"
    return path.read_text(encoding="utf-8").strip()
