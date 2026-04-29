from __future__ import annotations

from pathlib import Path

from embedded_test_agent.integrations.feishu import FeishuClient
from embedded_test_agent.models import AgentOutcome, TestContext, utc_now
from embedded_test_agent.utils import dump_json, tail_lines, write_text

from .base import BaseAgent


def _status_icon(status: str) -> str:
    return {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "SKIP": "⏭️"}.get(status, "ℹ️")


def build_feishu_text(ctx: TestContext) -> str:
    status = ctx.metrics.get("final_status", "UNKNOWN")
    lines = [
        f"{_status_icon(status)} 固件测试结果: {status}",
        f"项目: {ctx.metrics.get('project_name', '')}",
        f"目标板: {ctx.target}",
        f"分支/提交: {ctx.branch}/{ctx.commit}",
        f"变更文件数: {len(ctx.changed_files)}",
        f"风险标签: {', '.join(ctx.risk_tags) or '无'}",
    ]
    if ctx.hypotheses:
        top = ctx.hypotheses[0]
        lines.extend(
            [
                "",
                f"首要归因: {top.category} ({top.confidence:.2f})",
                "关键证据:",
                *[f"- {e}" for e in top.evidence[:3]],
                f"建议: {top.suggestion}",
                f"责任方向: {top.owner_hint or '待确认'}",
            ]
        )
    else:
        lines.append("未发现明确失败证据。")
    lines.append(f"报告目录: {ctx.output_dir}")
    return "\n".join(lines)


def render_markdown(ctx: TestContext) -> str:
    status = ctx.metrics.get("final_status", "UNKNOWN")
    lines: list[str] = []
    lines.append(f"# Firmware Test Report - {status}\n")
    lines.append(f"- Generated At: `{utc_now()}`")
    lines.append(f"- Project: `{ctx.metrics.get('project_name', '')}`")
    lines.append(f"- Target: `{ctx.target}`")
    lines.append(f"- Branch: `{ctx.branch}`")
    lines.append(f"- Commit: `{ctx.commit}`")
    lines.append(f"- Mode: `{'mock' if ctx.mock else 'real'}`")
    lines.append("")

    lines.append("## 1. Executive Summary\n")
    if status == "PASS":
        lines.append("测试通过，构建和运行日志中未发现明确失败信号。")
    elif ctx.hypotheses:
        top = ctx.hypotheses[0]
        lines.append(f"测试失败，首要归因为 **{top.category}**，置信度 **{top.confidence:.2f}**。")
    else:
        lines.append("测试状态不确定，自动归因证据不足，建议人工复核完整日志。")
    lines.append("")

    lines.append("## 2. Structured Evidence Chain\n")
    lines.append("这是面向工程审计的显式证据链，不是模型私有思考过程。")
    lines.append("")
    lines.append("1. **提交证据**：分析变更文件和 diff，识别驱动、配置、RTOS、外设风险。")
    lines.append("2. **构建证据**：检查编译/链接错误、警告和工具链退出码。")
    lines.append("3. **烧录证据**：确认固件是否成功下载到目标板。")
    lines.append("4. **运行证据**：采集串口/测试脚本日志，提取异常信号。")
    lines.append("5. **历史证据**：匹配历史问题库，复用过往根因和修复建议。")
    lines.append("6. **结论证据**：输出故障类别、置信度、复现步骤和修复建议。")
    lines.append("")

    lines.append("## 3. Changed Files and Risk Tags\n")
    if ctx.changed_files:
        for item in ctx.changed_files:
            lines.append(f"- `{item}`")
    else:
        lines.append("- No changed files detected.")
    lines.append("")
    lines.append(f"Risk Tags: `{', '.join(ctx.risk_tags) or 'none'}`\n")

    lines.append("## 4. Agent Trace\n")
    lines.append("| Agent | Status | Duration(ms) | Summary |")
    lines.append("|---|---:|---:|---|")
    for step in ctx.step_trace:
        lines.append(f"| {step.name} | {step.status} | {step.duration_ms} | {step.summary.replace('|', '/')} |")
    lines.append("")

    lines.append("## 5. Failure Hypotheses\n")
    if not ctx.hypotheses:
        lines.append("No failure hypothesis generated.")
    for idx, hyp in enumerate(ctx.hypotheses, start=1):
        lines.append(f"### {idx}. {hyp.category} / confidence={hyp.confidence:.2f}")
        lines.append(f"- Owner Hint: `{hyp.owner_hint or 'unknown'}`")
        if hyp.related_files:
            lines.append(f"- Related Files: {', '.join(f'`{p}`' for p in hyp.related_files)}")
        lines.append("- Evidence:")
        for e in hyp.evidence:
            lines.append(f"  - {e}")
        lines.append(f"- Suggestion: {hyp.suggestion}")
        lines.append("")

    lines.append("## 6. Reproduction Steps\n")
    lines.append("1. Checkout the same branch and commit.")
    lines.append("2. Run the configured build command.")
    lines.append("3. Flash firmware with the configured flashing command.")
    lines.append("4. Capture serial logs using the configured baudrate and timeout.")
    lines.append("5. Compare output with `build.log`, `flash.log`, `serial.log` in this report directory.")
    lines.append("")

    lines.append("## 7. Key Log Tail\n")
    lines.append("### Build Log Tail")
    lines.append("```text")
    lines.append(tail_lines(ctx.build_log, 40))
    lines.append("```")
    lines.append("### Serial Log Tail")
    lines.append("```text")
    lines.append(tail_lines(ctx.serial_log, 60))
    lines.append("```")
    lines.append("")

    lines.append("## 8. Artifacts\n")
    for name, path in ctx.artifacts.items():
        lines.append(f"- `{name}`: `{path}`")
    lines.append("")
    return "\n".join(lines)


class ReportAgent(BaseAgent):
    name = "ReportAgent"

    def run(self, ctx: TestContext) -> AgentOutcome:
        markdown = render_markdown(ctx)
        report_path = write_text(Path(ctx.output_dir) / "report.md", markdown)
        ctx.add_artifact("report_md", report_path)

        trace_path = dump_json(Path(ctx.output_dir) / "agent_trace.json", [s.to_dict() for s in ctx.step_trace])
        ctx.add_artifact("agent_trace", trace_path)

        report_json = {
            "status": ctx.metrics.get("final_status", "UNKNOWN"),
            "project": ctx.metrics.get("project_name", ""),
            "target": ctx.target,
            "branch": ctx.branch,
            "commit": ctx.commit,
            "changed_files": ctx.changed_files,
            "risk_tags": ctx.risk_tags,
            "hypotheses": [h.to_dict() for h in ctx.hypotheses],
            "metrics": ctx.metrics,
            "artifacts": ctx.artifacts,
            "observations": ctx.observations,
        }
        json_path = dump_json(Path(ctx.output_dir) / "report.json", report_json)
        ctx.add_artifact("report_json", json_path)

        feishu_text = build_feishu_text(ctx)
        feishu_path = write_text(Path(ctx.output_dir) / "feishu_message.txt", feishu_text)
        ctx.add_artifact("feishu_message", feishu_path)

        feishu_result = {"sent": False, "error": "disabled"}
        feishu_cfg = ctx.config.get("feishu", {})
        if ctx.feishu_enabled and feishu_cfg.get("enabled", True):
            client = FeishuClient(
                webhook_url=str(feishu_cfg.get("webhook_url", "")),
                secret=str(feishu_cfg.get("secret", "")),
            )
            feishu_result = client.send_text(feishu_text).to_dict()
        feishu_result_path = dump_json(Path(ctx.output_dir) / "feishu_result.json", feishu_result)
        ctx.add_artifact("feishu_result", feishu_result_path)

        summary = f"报告已生成: {report_path}"
        if feishu_result.get("sent"):
            summary += "；飞书通知已发送。"
        else:
            summary += "；飞书通知未发送或被跳过。"
        return AgentOutcome(status="PASS", summary=summary, artifacts={"report_md": report_path, "report_json": json_path})
