#!/usr/bin/env bash
set -euo pipefail

: "${FEISHU_WEBHOOK_URL:?Set FEISHU_WEBHOOK_URL first}"

python -m embedded_test_agent run \
  --repo examples/firmware \
  --config configs/demo.json \
  --mock
