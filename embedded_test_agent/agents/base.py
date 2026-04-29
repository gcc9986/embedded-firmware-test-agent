from __future__ import annotations

import time
from abc import ABC, abstractmethod

from embedded_test_agent.models import AgentOutcome, AgentStep, TestContext, utc_now


class BaseAgent(ABC):
    name = "BaseAgent"

    def execute(self, ctx: TestContext) -> AgentOutcome:
        started = time.perf_counter()
        step = AgentStep(name=self.name, status="UNKNOWN", summary="", started_at=utc_now())
        try:
            outcome = self.run(ctx)
            step.status = outcome.status
            step.summary = outcome.summary
            step.artifacts = dict(outcome.artifacts)
            step.observations = list(outcome.observations)
            return outcome
        except Exception as exc:
            outcome = AgentOutcome(status="FAIL", summary=f"{self.name} failed: {exc}")
            step.status = outcome.status
            step.summary = outcome.summary
            ctx.add_observation(outcome.summary)
            return outcome
        finally:
            step.finished_at = utc_now()
            step.duration_ms = int((time.perf_counter() - started) * 1000)
            ctx.step_trace.append(step)

    @abstractmethod
    def run(self, ctx: TestContext) -> AgentOutcome:
        raise NotImplementedError
