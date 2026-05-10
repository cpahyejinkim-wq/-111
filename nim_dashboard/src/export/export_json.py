from __future__ import annotations

import json
from pathlib import Path

from src.common import json_sanitize


def write_json(data, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(json_sanitize(data), ensure_ascii=False, indent=2), encoding="utf-8")
