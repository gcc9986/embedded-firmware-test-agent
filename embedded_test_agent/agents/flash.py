from __future__ import annotations

from pathlib import Path

from embedded_test_agent.integrations.shell import run_command
from embedded_test_agent.models import AgentOutcome, TestContext
from embedded_test_agent.utils import resolve_path, write_text

from .base import BaseAgent


class FlashAgent(BaseAgent):
    name = "FlashAgent"

    def run(self, ctx: TestContext) -> AgentOutcome:
        if ctx.metrics.get("build", {}).get("failed"):
            msg = "构建失败，跳过烧录。"
            ctx.flash_log = msg
            path = write_text(Path(ctx.output_dir) / "flash.log", msg + "\n")
            ctx.add_artifact("flash_log", path)
            return AgentOutcome(status="SKIP", summary=msg, artifacts={"flash_log": path})

        cfg = ctx.config.get("flash", {})
        if cfg.get("skip"):
            msg = "配置要求跳过烧录。"
            ctx.flash_log = msg
            path = write_text(Path(ctx.output_dir) / "flash.log", msg + "\n")
            ctx.add_artifact("flash_log", path)
            return AgentOutcome(status="SKIP", summary=msg, artifacts={"flash_log": path})

        if ctx.mock:
            log = f"MOCK FLASH OK: target={ctx.target}, commit={ctx.commit}\n"
            status = "PASS"
        else:
            repo = Path(ctx.repo_path).resolve()
            command = str(cfg.get("command", "echo flash"))
            cwd = Path(resolve_path(str(cfg.get("cwd", ".")), base=repo) or repo)
            timeout = int(cfg.get("timeout_sec", 60))
            result = run_command(command, cwd=cwd, timeout_sec=timeout)
            log = result.combined_output
            ctx.metrics["flash_returncode"] = result.returncode
            ctx.metrics["flash_duration_ms"] = result.duration_ms
            status = "PASS" if result.returncode == 0 else "FAIL"

        ctx.flash_log = log
        path = write_text(Path(ctx.output_dir) / "flash.log", log)
        ctx.add_artifact("flash_log", path)
        msg = "烧录完成。" if status == "PASS" else "烧录失败。"
        ctx.add_observation(msg)
        return AgentOutcome(status=status, summary=msg, artifacts={"flash_log": path})
