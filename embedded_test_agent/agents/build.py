from __future__ import annotations

from pathlib import Path

from embedded_test_agent.integrations.ci import summarize_build_log
from embedded_test_agent.integrations.shell import run_command
from embedded_test_agent.models import AgentOutcome, TestContext
from embedded_test_agent.utils import read_text, resolve_path, write_text

from .base import BaseAgent


class BuildAgent(BaseAgent):
    name = "BuildAgent"

    def run(self, ctx: TestContext) -> AgentOutcome:
        cfg = ctx.config.get("build", {})
        repo = Path(ctx.repo_path).resolve()
        log = ""
        status = "PASS"
        observations: list[str] = []

        if ctx.mock:
            mock_log = cfg.get("mock_log", "examples/logs/build_success.log")
            path = Path(resolve_path(mock_log, base=Path.cwd()) or mock_log)
            if not path.exists():
                path = Path(resolve_path(mock_log, base=repo) or mock_log)
            log = read_text(path, default="Build succeeded.\n")
            observations.append(f"mock 构建日志: {path}")
        else:
            command = str(cfg.get("command", "make all"))
            cwd = Path(resolve_path(str(cfg.get("cwd", ".")), base=repo) or repo)
            timeout = int(cfg.get("timeout_sec", 120))
            result = run_command(command, cwd=cwd, timeout_sec=timeout)
            log = result.combined_output
            ctx.metrics["build_returncode"] = result.returncode
            ctx.metrics["build_duration_ms"] = result.duration_ms
            if result.returncode != 0:
                status = "FAIL"
            observations.append(f"构建命令退出码: {result.returncode}")

        summary = summarize_build_log(log)
        ctx.metrics["build"] = summary.to_dict()
        if summary.failed:
            status = "FAIL"
        ctx.build_log = log
        path = write_text(Path(ctx.output_dir) / "build.log", log)
        ctx.add_artifact("build_log", path)

        if status == "PASS":
            msg = "固件构建完成，未发现明确编译/链接错误。"
        else:
            msg = f"固件构建失败，发现 {summary.error_count} 条关键错误。"
        ctx.add_observation(msg)
        return AgentOutcome(status=status, summary=msg, artifacts={"build_log": path}, observations=observations)
