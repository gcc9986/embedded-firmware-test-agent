from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .utils import deep_merge, load_json


def default_config() -> dict[str, Any]:
    return {
        "project_name": "Embedded Firmware Test Agent",
        "artifacts_dir": "reports",
        "git": {
            "diff_base": "HEAD~1",
            "diff_head": "HEAD",
            "mock_changed_files": [],
            "mock_diff": "",
        },
        "build": {
            "command": "make all",
            "cwd": ".",
            "timeout_sec": 120,
            "mock_log": "examples/logs/build_success.log",
        },
        "flash": {
            "command": "echo flash",
            "timeout_sec": 60,
            "skip": False,
        },
        "serial": {
            "port": None,
            "baudrate": 115200,
            "timeout_sec": 10,
            "mock_log": "examples/logs/serial_i2c_timeout.log",
            "until_patterns": ["TEST_DONE", "ASSERT", "HardFault", "panic", "watchdog"],
        },
        "history": {
            "issues_path": "data/history_issues.jsonl",
        },
        "feishu": {
            "enabled": True,
            "webhook_url_env": "FEISHU_WEBHOOK_URL",
            "secret_env": "FEISHU_WEBHOOK_SECRET",
        },
        "llm": {
            "enabled": False,
            "provider": "openai_compatible",
        },
    }


def load_config(path: str | None = None) -> dict[str, Any]:
    cfg = default_config()
    if path:
        loaded = load_json(path, default={}) or {}
        cfg = deep_merge(cfg, loaded)
        cfg["_config_path"] = str(Path(path).resolve())
        cfg["_config_dir"] = str(Path(path).resolve().parent)
    else:
        cfg["_config_path"] = ""
        cfg["_config_dir"] = str(Path.cwd())

    feishu = cfg.setdefault("feishu", {})
    url_env = feishu.get("webhook_url_env", "FEISHU_WEBHOOK_URL")
    secret_env = feishu.get("secret_env", "FEISHU_WEBHOOK_SECRET")
    feishu["webhook_url"] = os.getenv(url_env, feishu.get("webhook_url", ""))
    feishu["secret"] = os.getenv(secret_env, feishu.get("secret", ""))
    return cfg
