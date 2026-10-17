"""Step tracing for the document pipeline and the benefits check.

Not telemetry or logging infrastructure -- this exists for one reason:
to give the user (and anyone reviewing this project) an honest,
visible record of which steps were handled by an OCI AI service and
which were handled by deterministic code. "Checked eligibility -> Rules
engine (no AI)" is the single most important line this produces -- it's
the proof, not just the claim, that the LLM never decides eligibility.
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

from pydantic import BaseModel


def is_mock_mode() -> bool:
    return os.getenv("MOCK_MODE", "true").lower() not in ("0", "false", "no")


def mock_suffix() -> str:
    return " (mock)" if is_mock_mode() else ""


@dataclass
class TraceStep:
    name: str
    service: str
    duration_ms: float
    success: bool


@dataclass
class Trace:
    steps: list[TraceStep] = field(default_factory=list)

    @contextmanager
    def step(self, name: str, service: str):
        start = time.perf_counter()
        ok = True
        try:
            yield
        except Exception:
            ok = False
            raise
        finally:
            self.steps.append(
                TraceStep(
                    name=name,
                    service=service,
                    duration_ms=round((time.perf_counter() - start) * 1000, 1),
                    success=ok,
                )
            )


class TraceStepOut(BaseModel):
    name: str
    service: str
    duration_ms: float
    success: bool


def trace_to_out(trace: Trace) -> list[TraceStepOut]:
    return [TraceStepOut(name=s.name, service=s.service, duration_ms=s.duration_ms, success=s.success) for s in trace.steps]
