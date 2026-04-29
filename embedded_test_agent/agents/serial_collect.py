from __future__ import annotations

from pathlib import Path

from embedded_test_agent.integrations.serial_port import read_serial_log
from embedded_test_agent.models import AgentOutcome, TestContext
from embedded_test_agent.utils import read_text, resolve_path, write_text

from .base import BaseAgent


class SerialCollectAgent(BaseAgent):
    name = "SerialCollectAgent"

    def run(self, ctx: TestContext) -> AgentOutcome:
        if ctx.metrics.get("build", {}).get("failed"):
            msg = "构建失败，跳过串口采集。"
            ctx.serial_log = msg
            path = write_text(Path(ctx.output_dir) / "serial.log", msg + "\n")
            ctx.add_artifact("serial_log", path)
            return AgentOutcome(status="SKIP", summary=msg, artifacts={"serial_log": path})

        if ctx.step_trace and ctx.step_trace[-1].name == "FlashAgent" and ctx.step_trace[-1].status == "FAIL":
            msg = "烧录失败，跳过串口采集。"
            ctx.serial_log = msg
            path = write_text(Path(ctx.output_dir) / "serial.log", msg + "\n")
            ctx.add_artifact("serial_log", path)
            return AgentOutcome(status="SKIP", summary=msg, artifacts={"serial_log": path})

        cfg = ctx.config.get("serial", {})
        if ctx.mock:
            mock_log = cfg.get("mock_log", "examples/logs/serial_i2c_timeout.log")
            path_obj = Path(resolve_path(mock_log, base=Path.cwd()) or mock_log)
            if not path_obj.exists():
                path_obj = Path(resolve_path(mock_log, base=Path(ctx.repo_path).resolve()) or mock_log)
            log = read_text(path_obj, default="[00:00.000] test: TEST_DONE status=PASS\n")
            observation = f"mock 串口日志: {path_obj}"
        else:
            port = cfg.get("port")
            if not port:
                msg = "未配置串口端口，跳过运行日志采集。"
                ctx.serial_log = msg
                path = write_text(Path(ctx.output_dir) / "serial.log", msg + "\n")
                ctx.add_artifact("serial_log", path)
                return AgentOutcome(status="WARN", summary=msg, artifacts={"serial_log": path})
            log = read_serial_log(
                port=str(port),
                baudrate=int(cfg.get("baudrate", 115200)),
                timeout_sec=int(cfg.get("timeout_sec", 10)),
                until_patterns=cfg.get("until_patterns", []),
            )
            observation = f"串口采集完成: port={port}, lines={len(log.splitlines())}"

        ctx.serial_log = log
        path = write_text(Path(ctx.output_dir) / "serial.log", log)
        ctx.add_artifact("serial_log", path)
        ctx.add_observation(observation)
        return AgentOutcome(status="PASS", summary="串口/运行日志采集完成。", artifacts={"serial_log": path}, observations=[observation])
