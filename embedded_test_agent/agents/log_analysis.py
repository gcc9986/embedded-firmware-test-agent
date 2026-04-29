from __future__ import annotations

from pathlib import Path

from embedded_test_agent.integrations.llm import LLMClient
from embedded_test_agent.models import AgentOutcome, TestContext
from embedded_test_agent.rules import classify_failure
from embedded_test_agent.utils import dump_json, resolve_path, tail_lines, write_text

from .base import BaseAgent


class LogAnalysisAgent(BaseAgent):
    name = "LogAnalysisAgent"

    def run(self, ctx: TestContext) -> AgentOutcome:
        history_cfg = ctx.config.get("history", {})
        history_path = history_cfg.get("issues_path")
        history_abs = resolve_path(history_path, base=Path.cwd()) if history_path else None
        if history_abs and not Path(history_abs).exists():
            history_abs = resolve_path(history_path, base=Path(ctx.repo_path).resolve())

        status, hypotheses = classify_failure(
            build_log=ctx.build_log,
            serial_log=ctx.serial_log,
            ci_log=ctx.ci_log,
            changed_files=ctx.changed_files,
            risk_tags=ctx.risk_tags,
            history_path=history_abs,
        )
        ctx.hypotheses = hypotheses
        ctx.metrics["final_status"] = status
        ctx.metrics["hypothesis_count"] = len(hypotheses)

        llm_cfg = ctx.config.get("llm", {})
        llm_summary = ""
        if llm_cfg.get("enabled"):
            client = LLMClient(enabled=True, model=llm_cfg.get("model"))
            user_prompt = (
                "请基于以下嵌入式测试证据输出简短结论、可能原因和修复建议。\n"
                f"变更文件: {ctx.changed_files}\n"
                f"风险标签: {ctx.risk_tags}\n"
                f"构建日志尾部:\n{tail_lines(ctx.build_log, 60)}\n"
                f"串口日志尾部:\n{tail_lines(ctx.serial_log, 80)}\n"
            )
            try:
                llm_summary = client.summarize(
                    "你是嵌入式固件测试和故障定位专家。只输出可验证工程结论，不编造证据。",
                    user_prompt,
                )
            except Exception as exc:
                llm_summary = f"LLM 总结失败，已保留规则引擎结论: {exc}"
        if llm_summary:
            ctx.metrics["llm_summary"] = llm_summary
            llm_path = write_text(Path(ctx.output_dir) / "llm_summary.md", llm_summary)
            ctx.add_artifact("llm_summary", llm_path)

        hyp_path = dump_json(Path(ctx.output_dir) / "hypotheses.json", [h.to_dict() for h in hypotheses])
        ctx.add_artifact("hypotheses", hyp_path)

        if status == "PASS":
            msg = "未发现明确失败证据，测试判断为 PASS。"
        elif status == "UNKNOWN":
            msg = "证据不足，无法自动归因，建议人工复核完整日志。"
        else:
            top = hypotheses[0]
            msg = f"测试失败，首要归因为 {top.category}，置信度 {top.confidence:.2f}。"
        ctx.add_observation(msg)
        return AgentOutcome(status=status if status in {"PASS", "FAIL"} else "WARN", summary=msg, artifacts={"hypotheses": hyp_path})
