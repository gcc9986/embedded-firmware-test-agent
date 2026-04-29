from __future__ import annotations

from pathlib import Path

from embedded_test_agent.integrations.git_client import changed_files, diff_text
from embedded_test_agent.models import AgentOutcome, TestContext
from embedded_test_agent.rules import infer_risk_tags
from embedded_test_agent.utils import write_text

from .base import BaseAgent


class CodeAnalysisAgent(BaseAgent):
    name = "CodeAnalysisAgent"

    def run(self, ctx: TestContext) -> AgentOutcome:
        git_cfg = ctx.config.get("git", {})
        repo = Path(ctx.repo_path).resolve()

        if ctx.mock and git_cfg.get("mock_changed_files"):
            ctx.changed_files = list(git_cfg.get("mock_changed_files", []))
            ctx.diff = str(git_cfg.get("mock_diff", ""))
        else:
            ctx.changed_files = changed_files(repo, ctx.base_ref, ctx.head_ref)
            ctx.diff = diff_text(repo, ctx.base_ref, ctx.head_ref)

        for tag in infer_risk_tags(ctx.changed_files, ctx.diff):
            ctx.add_risk_tag(tag)

        changed_path = write_text(Path(ctx.output_dir) / "changed_files.txt", "\n".join(ctx.changed_files))
        diff_path = write_text(Path(ctx.output_dir) / "code_diff.patch", ctx.diff or "# No diff available\n")
        ctx.add_artifact("changed_files", changed_path)
        ctx.add_artifact("code_diff", diff_path)

        if ctx.changed_files:
            summary = f"识别到 {len(ctx.changed_files)} 个变更文件，风险标签: {', '.join(ctx.risk_tags) or '无'}。"
        else:
            summary = "未识别到变更文件，后续将主要依赖构建和运行日志判断。"
        observations = [summary]
        ctx.add_observation(summary)
        return AgentOutcome(
            status="PASS",
            summary=summary,
            artifacts={"changed_files": changed_path, "code_diff": diff_path},
            observations=observations,
        )
