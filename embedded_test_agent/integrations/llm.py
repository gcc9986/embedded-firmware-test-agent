from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


class LLMClient:
    """Small OpenAI-compatible client used only when explicitly enabled.

    The project works without an LLM key. The rule engine remains the default path,
    which makes local demos and CI deterministic.
    """

    def __init__(self, enabled: bool = False, model: str | None = None) -> None:
        self.enabled = enabled
        self.api_base = os.getenv("LLM_API_BASE", "").rstrip("/")
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

    def summarize(self, system_prompt: str, user_prompt: str) -> str:
        if not self.enabled or not self.api_base or not self.api_key:
            return ""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.api_base}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            result = json.loads(resp.read().decode("utf-8"))
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")
