from __future__ import annotations

import json
from pathlib import Path


def load_aliases(path: str | None) -> dict[str, list[str]]:
    if not path or not Path(path).exists():
        return {}
    data = json.loads(Path(path).read_text())
    return data.get("aliases", {})
