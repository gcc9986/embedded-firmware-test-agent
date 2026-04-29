from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class BuildSummary:
    failed: bool
    error_count: int
    warning_count: int
    key_lines: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "failed": self.failed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "key_lines": self.key_lines,
        }


ERROR_PATTERNS = [
    re.compile(r"\berror:\b", re.IGNORECASE),
    re.compile(r"fatal error", re.IGNORECASE),
    re.compile(r"undefined reference", re.IGNORECASE),
    re.compile(r"multiple definition", re.IGNORECASE),
    re.compile(r"No such file or directory", re.IGNORECASE),
    re.compile(r"collect2: error", re.IGNORECASE),
    re.compile(r"make\[.*\]: \*\*\*", re.IGNORECASE),
]

WARNING_RE = re.compile(r"\bwarning:\b", re.IGNORECASE)


def summarize_build_log(log: str) -> BuildSummary:
    key_lines: list[str] = []
    error_count = 0
    warning_count = 0
    for line in log.splitlines():
        if any(p.search(line) for p in ERROR_PATTERNS):
            error_count += 1
            if len(key_lines) < 20:
                key_lines.append(line.strip())
        elif WARNING_RE.search(line):
            warning_count += 1
            if len(key_lines) < 20:
                key_lines.append(line.strip())
    return BuildSummary(
        failed=error_count > 0,
        error_count=error_count,
        warning_count=warning_count,
        key_lines=key_lines,
    )
