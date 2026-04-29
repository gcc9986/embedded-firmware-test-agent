from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from embedded_test_agent.utils import redact_secret


@dataclass
class CommandResult:
    command: str
    cwd: str
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int

    @property
    def combined_output(self) -> str:
        return redact_secret((self.stdout or "") + ("\n" if self.stdout and self.stderr else "") + (self.stderr or ""))


def run_command(command: str, cwd: str | Path = ".", timeout_sec: int = 120) -> CommandResult:
    started = time.perf_counter()
    cwd_path = str(Path(cwd).resolve())
    try:
        proc = subprocess.run(
            command,
            cwd=cwd_path,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        return CommandResult(
            command=command,
            cwd=cwd_path,
            returncode=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return CommandResult(
            command=command,
            cwd=cwd_path,
            returncode=124,
            stdout=stdout,
            stderr=stderr + f"\nTIMEOUT after {timeout_sec}s",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
