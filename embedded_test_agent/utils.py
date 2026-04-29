from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_text(path: str | Path, default: str = "") -> str:
    p = Path(path)
    if not p.exists():
        return default
    return p.read_text(encoding="utf-8", errors="replace")


def write_text(path: str | Path, content: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return str(p)


def load_json(path: str | Path, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def dump_json(path: str | Path, data: Any) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def resolve_path(path: str | None, *, base: str | Path | None = None) -> str | None:
    if not path:
        return path
    p = Path(path).expanduser()
    if p.is_absolute():
        return str(p)
    if base is None:
        return str(p)
    return str((Path(base) / p).resolve())


def redact_secret(text: str) -> str:
    if not text:
        return text
    secrets = ["FEISHU_WEBHOOK_URL", "FEISHU_WEBHOOK_SECRET", "LLM_API_KEY"]
    result = text
    for env_name in secrets:
        value = os.getenv(env_name)
        if value:
            result = result.replace(value, "***REDACTED***")
    return result


def tail_lines(text: str, limit: int = 80) -> str:
    lines = text.splitlines()
    if len(lines) <= limit:
        return text
    return "\n".join(lines[-limit:])
