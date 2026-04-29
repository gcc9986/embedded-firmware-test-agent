from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class FeishuSendResult:
    sent: bool
    status_code: int = 0
    response: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "sent": self.sent,
            "status_code": self.status_code,
            "response": self.response,
            "error": self.error,
        }


class FeishuClient:
    def __init__(self, webhook_url: str = "", secret: str = "", timeout_sec: int = 10) -> None:
        self.webhook_url = webhook_url
        self.secret = secret
        self.timeout_sec = timeout_sec

    @staticmethod
    def sign(timestamp: str, secret: str) -> str:
        string_to_sign = f"{timestamp}\n{secret}"
        digest = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")

    def send_text(self, text: str) -> FeishuSendResult:
        if not self.webhook_url:
            return FeishuSendResult(sent=False, error="FEISHU_WEBHOOK_URL is not configured")
        timestamp = str(int(time.time()))
        payload: dict[str, Any] = {
            "msg_type": "text",
            "content": {"text": text[:3500]},
        }
        if self.secret:
            payload["timestamp"] = timestamp
            payload["sign"] = self.sign(timestamp, self.secret)

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:  # noqa: S310
                body = resp.read().decode("utf-8", errors="replace")
                return FeishuSendResult(sent=True, status_code=resp.status, response=body)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return FeishuSendResult(sent=False, status_code=exc.code, response=body, error=str(exc))
        except Exception as exc:
            return FeishuSendResult(sent=False, error=str(exc))
