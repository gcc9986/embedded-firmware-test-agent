from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except ImportError as exc:
    raise RuntimeError("FastAPI server dependencies are missing. Install with: pip install fastapi uvicorn") from exc

from .config import load_config
from .models import TestContext
from .orchestrator import EmbeddedTestOrchestrator


class RunRequest(BaseModel):
    repo: str = Field(default_factory=lambda: os.getenv("AGENT_DEFAULT_REPO", "."))
    config: str = Field(default_factory=lambda: os.getenv("AGENT_DEFAULT_CONFIG", "configs/demo.json"))
    base_ref: str | None = None
    head_ref: str | None = None
    branch: str = "unknown"
    commit: str = "unknown"
    target: str = "default"
    mock: bool = False
    no_feishu: bool = False
    output_dir: str | None = None


app = FastAPI(title="Embedded Firmware Test Agent", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run")
def run_agent(req: RunRequest) -> dict[str, Any]:
    cfg = load_config(req.config)
    git_cfg = cfg.get("git", {})
    repo = Path(req.repo).expanduser().resolve()
    if not repo.exists():
        raise HTTPException(status_code=400, detail=f"repo does not exist: {repo}")
    output_dir = req.output_dir or str(Path(cfg.get("artifacts_dir", "reports")) / "webhook-latest")
    ctx = TestContext(
        repo_path=str(repo),
        branch=req.branch,
        commit=req.commit,
        base_ref=req.base_ref or git_cfg.get("diff_base", "HEAD~1"),
        head_ref=req.head_ref or git_cfg.get("diff_head", "HEAD"),
        target=req.target,
        mock=req.mock,
        output_dir=output_dir,
        config=cfg,
        feishu_enabled=not req.no_feishu,
    )
    result = EmbeddedTestOrchestrator().run(ctx)
    return {
        "status": result.metrics.get("final_status", "UNKNOWN"),
        "report": result.artifacts.get("report_md"),
        "report_json": result.artifacts.get("report_json"),
        "hypotheses": [h.to_dict() for h in result.hypotheses],
        "artifacts": result.artifacts,
    }


@app.post("/webhook/git")
def git_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    """Generic webhook adapter.

    Expected minimal payload:
    {
      "repo": "/path/to/repo",
      "base_ref": "origin/main",
      "head_ref": "HEAD",
      "branch": "feature/x",
      "commit": "abc123",
      "target": "dev-board-a",
      "mock": false
    }
    """
    req = RunRequest(
        repo=payload.get("repo") or os.getenv("AGENT_DEFAULT_REPO", "."),
        config=payload.get("config") or os.getenv("AGENT_DEFAULT_CONFIG", "configs/demo.json"),
        base_ref=payload.get("base_ref"),
        head_ref=payload.get("head_ref"),
        branch=payload.get("branch", "unknown"),
        commit=payload.get("commit", "unknown"),
        target=payload.get("target", "default"),
        mock=bool(payload.get("mock", False)),
        no_feishu=bool(payload.get("no_feishu", False)),
        output_dir=payload.get("output_dir"),
    )
    return run_agent(req)
