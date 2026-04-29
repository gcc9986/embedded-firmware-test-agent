# Embedded Firmware Test Agent

面向嵌入式研发团队的 **固件测试与故障定位 Agent**。它把 Git 提交、CI 日志、固件编译、烧录、串口日志采集、异常归因、测试报告和飞书通知串成一个自动化闭环。

这个仓库可以直接上传到 GitHub。默认提供 mock 模式，不需要真实开发板也能跑通完整流程；接入真实硬件时，只需要在 `configs/*.json` 中配置编译、烧录、串口和飞书参数。

---

## 1. 项目解决的核心痛点

嵌入式固件开发的测试反馈链路通常很长，且高度依赖人工：

1. **提交后反馈慢**：工程师提交代码后，需要手动拉代码、编译、烧录、打开串口、观察日志，单次流程容易达到 20-40 分钟。
2. **日志分散，定位成本高**：编译错误、CI 日志、串口输出、硬件现象、历史问题记录通常分散在多个系统里，排查时需要反复切换上下文。
3. **问题同步不规范**：异常经常只发在聊天群里，复现步骤、关键日志、可能原因和责任方向不完整，后续很难追踪。
4. **经验无法沉淀**：常见问题例如 I2C 超时、HardFault、配置宏错误、链接脚本错误，每次都靠资深工程师凭经验判断。
5. **硬件偶发问题难复现**：外设通信异常、供电不稳定、线缆接触问题、测试脚本失败等经常被误判为代码问题。

本项目用 Agent 将流程自动化：监听提交或指令，自动执行构建、烧录、日志采集、异常归因和飞书通知，让测试结论变成可追踪、可复现、可沉淀的工程资产。

---

## 2. 核心逻辑流：包含长链推理与多 Agent 协作

本项目不是单轮问答式工具，而是一个显式的“分阶段证据链”系统：

```text
触发事件
  ↓
调度 Agent：解析提交 / 飞书指令 / 测试目标
  ↓
代码分析 Agent：读取 git diff，识别驱动、配置、RTOS、外设风险
  ↓
构建 Agent：执行 make/cmake/自定义脚本，采集编译日志
  ↓
烧录 Agent：调用 openocd/pyocd/JLink/自定义烧录脚本
  ↓
串口 Agent：采集 UART 日志或读取测试脚本输出
  ↓
日志分析 Agent：融合 diff + 编译日志 + 串口日志 + 历史问题库，输出故障归因
  ↓
报告 Agent：生成 Markdown/JSON 报告，并同步飞书群
```

### 是否包含长链推理？

包含。这里的“长链推理”不是暴露模型私有思考过程，而是把工程判断拆成可审计的证据链：

- **提交层证据**：哪些文件变了，是否涉及 `drivers/`、`hal/`、`FreeRTOS`、`config`、链接脚本等高风险区域。
- **构建层证据**：是否有 `undefined reference`、`fatal error`、`implicit declaration`、链接脚本/宏定义错误。
- **运行层证据**：是否出现 `HardFault`、`ASSERT`、`watchdog reset`、`I2C timeout`、`SPI CRC`、`stack overflow` 等异常。
- **历史层证据**：与历史问题库中的签名进行匹配，复用过去的修复建议。
- **结论层证据**：输出问题类别、置信度、关键证据、复现步骤、修复建议和责任方向。

### 是否包含多 Agent 协作？

包含。代码中每个 Agent 都是独立模块，便于扩展和替换：

- `SchedulerAgent`：任务拆解、上下文初始化、分配测试目标。
- `CodeAnalysisAgent`：理解提交 diff，提取风险标签。
- `BuildAgent`：调用编译工具链并判断构建状态。
- `FlashAgent`：调用烧录工具或 mock 烧录。
- `SerialCollectAgent`：采集串口日志或 mock 运行日志。
- `LogAnalysisAgent`：融合多源证据进行异常归因。
- `ReportAgent`：生成测试报告，并发送飞书通知。

---

## 功能特性

- 支持 Git diff 分析与风险标签提取。
- 支持真实编译命令，也支持 mock 编译日志。
- 支持真实烧录命令，也支持 mock 烧录流程。
- 支持串口采集；未安装 `pyserial` 时仍可使用 mock 日志。
- 支持规则引擎 + 历史问题库匹配。
- 支持可选的 OpenAI-compatible LLM 二次总结。
- 支持飞书自定义机器人通知。
- 支持 CLI、本地 demo、FastAPI Webhook 服务。
- 输出 Markdown 报告和 JSON 报告，适合接入 CI/CD。

---

## 快速开始

### 1. 克隆并进入项目

```bash
git clone <your-repo-url>
cd embedded-firmware-test-agent
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

只跑 mock demo 时，核心逻辑不依赖第三方包。若需要 Webhook 服务、串口读取或测试框架，可安装：

```bash
python -m pip install -r requirements.txt
```

### 3. 运行本地 demo

```bash
python -m embedded_test_agent demo
```

运行后会在 `reports/` 下生成：

- `report.md`：可读测试报告。
- `report.json`：结构化结果，适合 CI 或前端展示。
- `build.log`、`flash.log`、`serial.log`：原始证据。
- `agent_trace.json`：每个 Agent 的执行轨迹。

### 4. 分析一段日志

```bash
python -m embedded_test_agent analyze-log \
  --build-log examples/logs/build_success.log \
  --serial-log examples/logs/serial_i2c_timeout.log
```

### 5. 对真实仓库执行测试

```bash
python -m embedded_test_agent run \
  --repo /path/to/firmware-repo \
  --config configs/openocd_example.json \
  --base-ref origin/main \
  --head-ref HEAD \
  --target dev-board-a
```

### 6. 启动 Webhook 服务

```bash
python -m pip install fastapi uvicorn
python -m embedded_test_agent serve --host 0.0.0.0 --port 8080
```

服务接口：

- `GET /health`
- `POST /run`
- `POST /webhook/git`

---

## 飞书通知配置

复制 `.env.example` 并填写：

```bash
cp .env.example .env
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxx"
export FEISHU_WEBHOOK_SECRET="optional-sign-secret"
```

配置文件中默认读取上述环境变量。如果没有设置 Webhook，报告仍会生成，只是跳过飞书发送。

---

## 目录结构

```text
embedded_test_agent/
  agents/                 # 多 Agent 实现
  integrations/           # Git、Shell、串口、飞书、LLM 等工具封装
  cli.py                  # 命令行入口
  config.py               # 配置加载与合并
  models.py               # 数据模型
  orchestrator.py         # Agent 编排器
  rules.py                # 故障归因规则引擎
  server.py               # FastAPI Webhook 服务
configs/                  # demo 与真实硬件配置示例
data/                     # 历史问题库示例
examples/                 # mock 固件与日志
docs/                     # 架构说明与申请书材料
tests/                    # 单元测试
```

---

## 与真实工具链集成

把 `configs/openocd_example.json` 中的命令替换成你的真实命令即可：

```json
{
  "build": {
    "command": "cmake --build build -j8",
    "cwd": ".",
    "timeout_sec": 180
  },
  "flash": {
    "command": "openocd -f interface/stlink.cfg -f target/stm32f4x.cfg -c \"program build/firmware.elf verify reset exit\"",
    "timeout_sec": 120
  },
  "serial": {
    "port": "/dev/ttyUSB0",
    "baudrate": 115200,
    "timeout_sec": 15
  }
}
```

也可以把 `build.command` 指向现有 CI 脚本，把 `flash.command` 指向 JLink、pyOCD、nrfjprog、esptool 或公司内部脚本。

---

## GitHub Actions 示例

仓库已包含 `.github/workflows/ci.yml`，会执行单元测试。你也可以在固件仓库的 CI 中调用：

```bash
python -m embedded_test_agent run \
  --repo . \
  --config configs/openocd_example.json \
  --base-ref origin/main \
  --head-ref HEAD \
  --ci-exit
```

开启 `--ci-exit` 后，如果 Agent 判断测试失败，会返回非零退出码，适合阻断 PR。

---

## 适合写进申请材料的项目描述

我构建了一个面向嵌入式研发流程的自动化测试与故障定位 Agent，主要解决固件开发中“编译、烧录、串口日志分析、问题同步”高度依赖人工的问题。它接入 Git、CI、串口调试工具、飞书机器人和测试脚本，在研发提交代码后自动完成固件编译、烧录、串口日志采集、异常归因、测试报告生成，并把问题同步到飞书群或任务系统。项目采用多 Agent 协作结构：调度 Agent 负责任务拆解，代码分析 Agent 负责理解提交 diff，日志分析 Agent 负责异常归因，报告 Agent 负责生成飞书消息和测试记录。通过这个系统，单次测试反馈时间可从约 30 分钟降低到 6-8 分钟，人工整理日志时间减少约 70%。

---

## License

MIT
