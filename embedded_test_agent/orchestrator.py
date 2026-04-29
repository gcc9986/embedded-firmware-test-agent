from __future__ import annotations

from pathlib import Path

from .agents.build import BuildAgent
from .agents.code_analysis import CodeAnalysisAgent
from .agents.flash import FlashAgent
from .agents.log_analysis import LogAnalysisAgent
from .agents.report import ReportAgent
from .agents.scheduler import SchedulerAgent
from .agents.serial_collect import SerialCollectAgent
from .models import TestContext
from .utils import ensure_dir


class EmbeddedTestOrchestrator:
    """Coordinates the multi-agent firmware test workflow."""

    def __init__(self) -> None:
        self.agents = [
            SchedulerAgent(),
            CodeAnalysisAgent(),
            BuildAgent(),
            FlashAgent(),
            SerialCollectAgent(),
            LogAnalysisAgent(),
            ReportAgent(),
        ]

    def run(self, ctx: TestContext) -> TestContext:
        ensure_dir(Path(ctx.output_dir))
        for agent in self.agents:
            agent.execute(ctx)
        return ctx
