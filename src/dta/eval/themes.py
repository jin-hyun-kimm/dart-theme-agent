from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

THEMES_PATH = Path(__file__).parent / "themes.yaml"


@dataclass(frozen=True)
class Theme:
    id: str
    name: str
    etf_ticker: str
    etf_name: str
    description: str


def load_themes(path: Path = THEMES_PATH) -> tuple[str, list[Theme]]:
    d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    themes = [Theme(**t) for t in (d.get("themes") or [])]
    return str(d.get("date", "")), themes
