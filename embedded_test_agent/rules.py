from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import FailureHypothesis


RULES: list[dict[str, Any]] = [
    {
        "category": "BUILD_CONFIG_ERROR",
        "patterns": [r"fatal error: .*No such file", r"No such file or directory", r"implicit declaration", r"unknown type name"],
        "confidence": 0.88,
        "suggestion": "优先检查头文件路径、宏定义开关、CMakeLists.txt/Makefile 是否包含新增文件，以及目标芯片配置是否正确。",
        "owner_hint": "固件构建/配置",
    },
    {
        "category": "BUILD_LINK_ERROR",
        "patterns": [r"undefined reference", r"multiple definition", r"ld returned", r"collect2: error"],
        "confidence": 0.9,
        "suggestion": "检查新增源文件是否加入构建系统、符号是否重复定义、链接脚本和库链接顺序是否正确。",
        "owner_hint": "固件构建/链接",
    },
    {
        "category": "PERIPHERAL_COMMUNICATION",
        "patterns": [r"I2C\d* timeout", r"i2c: .*timeout", r"SPI .*CRC", r"UART .*framing", r"CAN .*bus off"],
        "confidence": 0.86,
        "suggestion": "检查外设地址、时钟、pull-up/pull-down、电源稳定时间、总线速率、线缆连接，并确认驱动超时路径有正确返回。",
        "owner_hint": "驱动/硬件联调",
    },
    {
        "category": "MEMORY_OR_RTOS",
        "patterns": [r"HardFault", r"BusFault", r"MemManage", r"stack overflow", r"malloc failed", r"heap exhausted"],
        "confidence": 0.9,
        "suggestion": "打开 fault decoder、map 文件和栈水位监控，重点检查空指针、越界访问、中断上下文调用阻塞 API 和任务栈大小。",
        "owner_hint": "固件核心/RTOS",
    },
    {
        "category": "RUNTIME_ASSERTION",
        "patterns": [r"ASSERT failed", r"assertion .*failed", r"panic", r"abort"],
        "confidence": 0.78,
        "suggestion": "根据断言文件和行号回溯输入参数，检查最近 diff 是否改变了初始化顺序、配置宏或错误码处理。",
        "owner_hint": "应用/驱动",
    },
    {
        "category": "RUNTIME_TIMEOUT",
        "patterns": [r"watchdog", r"WDT reset", r"task timeout", r"deadlock", r"blocked for"],
        "confidence": 0.82,
        "suggestion": "检查轮询循环是否缺少超时、互斥锁是否未释放、外设等待是否可能永久阻塞。",
        "owner_hint": "应用/RTOS",
    },
    {
        "category": "HARDWARE_UNSTABLE",
        "patterns": [r"brownout", r"under voltage", r"over current", r"usb disconnect", r"flash verify failed"],
        "confidence": 0.75,
        "suggestion": "优先排查供电、电缆、接口接触、烧录器稳定性和开发板批次差异；必要时重复测试确认偶发性。",
        "owner_hint": "硬件/测试台架",
    },
]

RISK_KEYWORDS: list[tuple[str, str]] = [
    ("drivers/", "DRIVER_CHANGE"),
    ("hal/", "HAL_CHANGE"),
    ("bsp/", "BSP_CHANGE"),
    ("freertos", "RTOS_CHANGE"),
    ("rtos", "RTOS_CHANGE"),
    ("config", "CONFIG_CHANGE"),
    ("linker", "LINKER_CHANGE"),
    (".ld", "LINKER_CHANGE"),
    ("i2c", "I2C_TOUCH"),
    ("spi", "SPI_TOUCH"),
    ("uart", "UART_TOUCH"),
    ("can", "CAN_TOUCH"),
]


def infer_risk_tags(changed_files: list[str], diff: str = "") -> list[str]:
    haystack = "\n".join(changed_files).lower() + "\n" + diff.lower()
    tags: list[str] = []
    for keyword, tag in RISK_KEYWORDS:
        if keyword.lower() in haystack and tag not in tags:
            tags.append(tag)
    if any(p.endswith(("CMakeLists.txt", "Makefile")) or p.endswith((".cmake", ".mk")) for p in changed_files):
        tags.append("BUILD_SCRIPT_CHANGE")
    return tags


def _evidence_for_patterns(text: str, patterns: list[str], limit: int = 4) -> list[str]:
    evidence: list[str] = []
    for line in text.splitlines():
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                clean = line.strip()
                if clean and clean not in evidence:
                    evidence.append(clean)
                break
        if len(evidence) >= limit:
            break
    return evidence


def _related_files(changed_files: list[str], category: str) -> list[str]:
    if not changed_files:
        return []
    lowered = [(p, p.lower()) for p in changed_files]
    if category == "PERIPHERAL_COMMUNICATION":
        keywords = ("driver", "i2c", "spi", "uart", "can", "bsp", "hal")
    elif category.startswith("BUILD"):
        keywords = ("cmake", "makefile", ".mk", "config", "include")
    elif category == "MEMORY_OR_RTOS":
        keywords = ("rtos", "task", "isr", "interrupt", "mem", "heap", "stack")
    else:
        keywords = ("src", "app", "driver")
    return [p for p, low in lowered if any(k in low for k in keywords)][:8]


def load_history_issues(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    issues: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            issues.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return issues


def match_history(text: str, history_path: str | None, changed_files: list[str]) -> list[FailureHypothesis]:
    hypotheses: list[FailureHypothesis] = []
    lower_text = text.lower()
    for item in load_history_issues(history_path):
        signature = str(item.get("signature", ""))
        if signature and signature.lower() in lower_text:
            hypotheses.append(
                FailureHypothesis(
                    category=str(item.get("category", "HISTORY_MATCH")),
                    confidence=0.91,
                    evidence=[f"历史问题命中: {signature}", str(item.get("root_cause", ""))],
                    suggestion=str(item.get("suggestion", "参考历史问题修复方案。")),
                    owner_hint=str(item.get("owner_hint", "")),
                    source_agent="HistoryMatcher",
                    related_files=_related_files(changed_files, str(item.get("category", ""))),
                )
            )
    return hypotheses


def classify_failure(
    *,
    build_log: str = "",
    serial_log: str = "",
    ci_log: str = "",
    changed_files: list[str] | None = None,
    risk_tags: list[str] | None = None,
    history_path: str | None = None,
) -> tuple[str, list[FailureHypothesis]]:
    changed_files = changed_files or []
    risk_tags = risk_tags or []
    combined = "\n".join([build_log, ci_log, serial_log])
    hypotheses: list[FailureHypothesis] = []

    for rule in RULES:
        evidence = _evidence_for_patterns(combined, rule["patterns"])
        if not evidence:
            continue
        confidence = float(rule["confidence"])
        if rule["category"] == "PERIPHERAL_COMMUNICATION" and any(t.endswith("TOUCH") for t in risk_tags):
            confidence = min(0.97, confidence + 0.07)
        if rule["category"].startswith("BUILD") and "BUILD_SCRIPT_CHANGE" in risk_tags:
            confidence = min(0.97, confidence + 0.05)
        hypotheses.append(
            FailureHypothesis(
                category=rule["category"],
                confidence=confidence,
                evidence=evidence,
                suggestion=rule["suggestion"],
                owner_hint=rule["owner_hint"],
                related_files=_related_files(changed_files, rule["category"]),
            )
        )

    hypotheses.extend(match_history(combined, history_path, changed_files))
    hypotheses = sorted(hypotheses, key=lambda h: h.confidence, reverse=True)

    if not hypotheses:
        if "TEST_DONE status=PASS" in serial_log or "Build succeeded" in build_log:
            return "PASS", []
        return "UNKNOWN", []
    return "FAIL", hypotheses
