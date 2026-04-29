from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

Status = Literal["PASS", "FAIL", "WARN", "SKIP", "UNKNOWN"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class FailureHypothesis:
    category: str
    confidence: float
    evidence: list[str]
    suggestion: str
    owner_hint: str = ""
    source_agent: str = "LogAnalysisAgent"
    related_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["confidence"] = round(float(self.confidence), 3)
        return data


@dataclass
class AgentStep:
    name: str
    status: Status
    summary: str
    started_at: str
    finished_at: str = ""
    duration_ms: int = 0
    artifacts: dict[str, str] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentOutcome:
    status: Status
    summary: str
    artifacts: dict[str, str] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)


@dataclass
class TestContext:
    repo_path: str
    branch: str = "unknown"
    commit: str = "unknown"
    base_ref: str = "HEAD~1"
    head_ref: str = "HEAD"
    target: str = "default"
    mock: bool = False
    output_dir: str = "reports/latest"
    config: dict[str, Any] = field(default_factory=dict)
    feishu_enabled: bool = True

    changed_files: list[str] = field(default_factory=list)
    diff: str = ""
    build_log: str = ""
    flash_log: str = ""
    serial_log: str = ""
    ci_log: str = ""

    artifacts: dict[str, str] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)
    risk_tags: list[str] = field(default_factory=list)
    hypotheses: list[FailureHypothesis] = field(default_factory=list)
    step_trace: list[AgentStep] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def add_artifact(self, name: str, path: str) -> None:
        self.artifacts[name] = path

    def add_observation(self, message: str) -> None:
        if message and message not in self.observations:
            self.observations.append(message)

    def add_risk_tag(self, tag: str) -> None:
        if tag and tag not in self.risk_tags:
            self.risk_tags.append(tag)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["hypotheses"] = [h.to_dict() for h in self.hypotheses]
        data["step_trace"] = [s.to_dict() for s in self.step_trace]
        return data
