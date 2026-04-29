from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import load_config
from .models import TestContext
from .orchestrator import EmbeddedTestOrchestrator
from .rules import classify_failure, infer_risk_tags
from .utils import read_text, resolve_path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def make_context(args: argparse.Namespace, cfg: dict[str, Any]) -> TestContext:
    repo = Path(args.repo).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else Path(cfg.get("artifacts_dir", "reports")) / f"run-{timestamp()}"
    git_cfg = cfg.get("git", {})
    return TestContext(
        repo_path=str(repo),
        branch=getattr(args, "branch", "unknown") or "unknown",
        commit=getattr(args, "commit", "unknown") or "unknown",
        base_ref=getattr(args, "base_ref", None) or git_cfg.get("diff_base", "HEAD~1"),
        head_ref=getattr(args, "head_ref", None) or git_cfg.get("diff_head", "HEAD"),
        target=getattr(args, "target", "default") or "default",
        mock=bool(getattr(args, "mock", False)),
        output_dir=str(output_dir),
        config=cfg,
        feishu_enabled=not bool(getattr(args, "no_feishu", False)),
    )


def cmd_demo(args: argparse.Namespace) -> int:
    root = repo_root()
    cfg = load_config(str(root / "configs" / "demo.json"))
    args.repo = str(root / "examples" / "firmware")
    args.output_dir = str(root / "reports" / f"demo-{timestamp()}")
    args.mock = True
    args.no_feishu = getattr(args, "no_feishu", False)
    ctx = make_context(args, cfg)
    result = EmbeddedTestOrchestrator().run(ctx)
    print(json.dumps({
        "status": result.metrics.get("final_status"),
        "report": result.artifacts.get("report_md"),
        "report_json": result.artifacts.get("report_json"),
        "top_hypothesis": result.hypotheses[0].to_dict() if result.hypotheses else None,
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    ctx = make_context(args, cfg)
    result = EmbeddedTestOrchestrator().run(ctx)
    status = result.metrics.get("final_status", "UNKNOWN")
    print(json.dumps({
        "status": status,
        "report": result.artifacts.get("report_md"),
        "report_json": result.artifacts.get("report_json"),
        "hypotheses": [h.to_dict() for h in result.hypotheses],
    }, ensure_ascii=False, indent=2))
    if args.ci_exit and status != "PASS":
        return 2
    return 0


def cmd_analyze_log(args: argparse.Namespace) -> int:
    build_log = read_text(args.build_log, default="") if args.build_log else ""
    serial_log = read_text(args.serial_log, default="") if args.serial_log else ""
    changed_files = args.changed_file or []
    risk_tags = infer_risk_tags(changed_files, "")
    history_path = resolve_path(args.history, base=Path.cwd()) if args.history else None
    status, hypotheses = classify_failure(
        build_log=build_log,
        serial_log=serial_log,
        changed_files=changed_files,
        risk_tags=risk_tags,
        history_path=history_path,
    )
    print(json.dumps({
        "status": status,
        "risk_tags": risk_tags,
        "hypotheses": [h.to_dict() for h in hypotheses],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn  # type: ignore
    except ImportError:
        print("uvicorn is not installed. Run: python -m pip install fastapi uvicorn", file=sys.stderr)
        return 1
    uvicorn.run("embedded_test_agent.server:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="embedded-test-agent",
        description="Embedded firmware test and failure localization multi-agent workflow.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="Run local mock demo without hardware.")
    demo.add_argument("--no-feishu", action="store_true", help="Skip Feishu notification even if env is configured.")
    demo.set_defaults(func=cmd_demo)

    run = sub.add_parser("run", help="Run firmware test workflow.")
    run.add_argument("--repo", required=True, help="Firmware repository path.")
    run.add_argument("--config", default=os.getenv("AGENT_DEFAULT_CONFIG", "configs/demo.json"), help="Config JSON path.")
    run.add_argument("--base-ref", default=None, help="Git diff base ref.")
    run.add_argument("--head-ref", default=None, help="Git diff head ref.")
    run.add_argument("--branch", default="unknown", help="Branch name override.")
    run.add_argument("--commit", default="unknown", help="Commit hash override.")
    run.add_argument("--target", default="default", help="Board/test target name.")
    run.add_argument("--output-dir", default="", help="Output report directory.")
    run.add_argument("--mock", action="store_true", help="Use mock build/flash/serial logs.")
    run.add_argument("--no-feishu", action="store_true", help="Skip Feishu notification.")
    run.add_argument("--ci-exit", action="store_true", help="Return non-zero exit code when final status is not PASS.")
    run.set_defaults(func=cmd_run)

    analyze = sub.add_parser("analyze-log", help="Analyze existing build/serial logs only.")
    analyze.add_argument("--build-log", default="", help="Build log path.")
    analyze.add_argument("--serial-log", default="", help="Serial log path.")
    analyze.add_argument("--history", default="data/history_issues.jsonl", help="History issues JSONL path.")
    analyze.add_argument("--changed-file", action="append", default=[], help="Changed file path, can be repeated.")
    analyze.set_defaults(func=cmd_analyze_log)

    serve = sub.add_parser("serve", help="Start FastAPI webhook server.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(func=cmd_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
