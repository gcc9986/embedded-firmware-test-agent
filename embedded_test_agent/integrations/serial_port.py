from __future__ import annotations

import re
import time
from typing import Iterable


def read_serial_log(
    port: str,
    baudrate: int = 115200,
    timeout_sec: int = 10,
    until_patterns: Iterable[str] | None = None,
) -> str:
    try:
        import serial  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pyserial is not installed. Install with: pip install pyserial") from exc

    patterns = [re.compile(p, re.IGNORECASE) for p in (until_patterns or [])]
    deadline = time.time() + timeout_sec
    lines: list[str] = []
    with serial.Serial(port=port, baudrate=baudrate, timeout=0.2) as ser:  # type: ignore[attr-defined]
        while time.time() < deadline:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").rstrip()
            lines.append(line)
            if any(p.search(line) for p in patterns):
                break
    return "\n".join(lines)
