from __future__ import annotations

from pathlib import Path

from embedded_test_agent.integrations.git_client import current_branch, head_commit, is_git_repo
from embedded_test_agent.models import AgentOutcome, TestContext
from embedded_test_agent.utils import ensure_dir

from .base import BaseAgent


class SchedulerAgent(BaseAgent):
    name = "SchedulerAgent"

    def run(self, ctx: TestContext) -> AgentOutcome:
        repo = Path(ctx.repo_path).resolve()
        ensure_dir(ctx.output_dir)
        observations: list[str] = []

        if is_git_repo(repo):
            if ctx.branch == "unknown":
                ctx.branch = current_branch(repo)
            if ctx.commit == "unknown":
                ctx.commit = head_commit(repo)
            observations.append(f"Git 仓库已识别: branch={ctx.branch}, commit={ctx.commit}")
        else:
            observations.append("当前路径不是 Git 仓库，已切换到文件扫描/mock diff 模式。")

        if not ctx.target or ctx.target == "default":
            ctx.target = ctx.config.get("target", "dev-board-a" if ctx.mock else "default")
        ctx.metrics["project_name"] = ctx.config.get("project_name", "Embedded Firmware Test Agent")
        ctx.metrics["target"] = ctx.target
        ctx.metrics["mock"] = ctx.mock
        ctx.add_observation(f"测试目标: {ctx.target}")
        for item in observations:
            ctx.add_observation(item)
        return AgentOutcome(status="PASS", summary="任务上下文初始化完成。", observations=observations)
