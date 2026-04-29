# Architecture

## 目标

本项目把嵌入式固件研发测试过程抽象为一个多 Agent 闭环系统：每个 Agent 负责一类可验证任务，所有 Agent 共享同一个 `TestContext`，并把执行证据写入报告目录。

## 数据流

```text
TestContext
  ├── repo_path / branch / commit / target
  ├── changed_files / diff / risk_tags
  ├── build_log / flash_log / serial_log / ci_log
  ├── hypotheses
  ├── artifacts
  └── step_trace
```

## Agent 职责

| Agent | 输入 | 输出 | 失败处理 |
|---|---|---|---|
| SchedulerAgent | repo/config/target | 初始化上下文 | 非 Git 仓库进入扫描模式 |
| CodeAnalysisAgent | Git repo/mock diff | changed_files/risk_tags | 无 diff 时降级为空证据 |
| BuildAgent | build command/mock log | build.log/build metrics | 构建失败会阻止烧录和串口采集 |
| FlashAgent | flash command | flash.log | 烧录失败会阻止串口采集 |
| SerialCollectAgent | serial config/mock log | serial.log | 未配置串口时返回 WARN |
| LogAnalysisAgent | 多源日志 | hypotheses/final_status | 证据不足返回 UNKNOWN/WARN |
| ReportAgent | TestContext | report.md/report.json/飞书消息 | Webhook 缺失则只跳过发送 |

## 长链推理设计

系统采用显式、可审计的证据链，而不是让 LLM 一次性给出结论：

1. 代码变更分析：从 diff 和文件路径推断风险范围。
2. 构建结果分析：优先定位配置、头文件、链接和工具链问题。
3. 烧录结果分析：确认是否进入真实运行阶段。
4. 运行日志分析：匹配 HardFault、ASSERT、外设超时、watchdog 等模式。
5. 历史问题匹配：通过 signature 复用已有故障经验。
6. 结论生成：按置信度排序，给出建议和责任方向。

## 扩展点

- 新增硬件测试脚本：在 `configs/*.json` 中把 `flash.command` 或 `build.command` 指向你的脚本。
- 新增日志规则：编辑 `embedded_test_agent/rules.py` 的 `RULES`。
- 接入问题系统：在 `ReportAgent` 后新增 `IssueAgent`，调用 Jira、飞书任务或 GitHub Issues API。
- 接入更强 LLM：设置 `LLM_API_BASE`、`LLM_API_KEY`，并在配置中开启 `llm.enabled`。
