"""Step tracing + OCI fallback for the document pipeline and benefits check.

Two related jobs:
1. Trace: an honest, visible record of which steps were handled by an OCI
   AI service and which were handled by deterministic code. "Checked
   eligibility -> Rules engine (no AI)" is the proof, not just the claim,
   that the LLM never decides eligibility.
2. call_with_fallback: MOCK_MODE=true still means "never touch the
   network" (tests and local dev depend on that staying true -- zero
   network calls, fully deterministic). But when MOCK_MODE=false, this
   makes mock what it should actually be: a fallback used only when a
   real OCI call fails (missing credentials, network error, anything),
   never a silent default. Every step records whether it had to fall
   back, so the UI can show a visible "Offline mode" indicator instead
   of pretending a degraded response came from live OCI.
"""

from __future__ import annotations

import contextvars
import logging
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable, TypeVar

from pydantic import BaseModel

from app.privacy import describe_failure

T = TypeVar("T")

log = logging.getLogger("letterlens.oci")

_fallback_used: contextvars.ContextVar[bool] = contextvars.ContextVar("fallback_used", default=False)


def is_mock_mode() -> bool:
    return os.getenv("MOCK_MODE", "true").lower() not in ("0", "false", "no")


def mock_suffix() -> str:
    return " (mock)" if is_mock_mode() else ""


def reset_fallback_flag() -> None:
    _fallback_used.set(False)


def mark_fallback_used() -> None:
    _fallback_used.set(True)


def was_fallback_used() -> bool:
    return _fallback_used.get()


def call_with_fallback(real: Callable[[], T], mock: Callable[[], T]) -> T:
    """Try `real()`. If MOCK_MODE is on, or `real()` raises for any
    reason (no credentials, network down, SDK not installed), fall back
    to `mock()` and flag that the fallback was used."""
    if is_mock_mode():
        mark_fallback_used()
        return mock()
    try:
        return real()
    except Exception as exc:
        # Loud on purpose: a silent fallback makes canned demo data look
        # like a live OCI answer.
        # Error type/status only: messages can repeat letter contents.
        log.warning("Real OCI call failed (%s); using the offline fallback", describe_failure(exc))
        mark_fallback_used()
        return mock()


def call_real_or_sample(real: Callable[[], T], sample: Callable[[], T]) -> T:
    """For reading a letter's facts. MOCK_MODE=true: canned sample answer.
    Otherwise real only -- a failure raises instead of quietly substituting
    sample values that would then be saved into someone's profile."""
    if is_mock_mode():
        mark_fallback_used()
        return sample()
    return real()


@dataclass
class TraceStep:
    name: str
    service: str
    duration_ms: float
    success: bool
    offline: bool = False


@dataclass
class Trace:
    steps: list[TraceStep] = field(default_factory=list)

    @contextmanager
    def step(self, name: str, service: str):
        start = time.perf_counter()
        ok = True
        reset_fallback_flag()
        try:
            yield
        except Exception:
            ok = False
            raise
        finally:
            offline = was_fallback_used()
            label = service
            if offline and "(mock)" not in service:
                # Real OCI was attempted (MOCK_MODE=false) and failed --
                # distinguish this from the always-mock "(mock)" label so
                # it reads as a degradation, not the intended mode.
                label = f"{service} (offline fallback)"
            self.steps.append(
                TraceStep(
                    name=name,
                    service=label,
                    duration_ms=round((time.perf_counter() - start) * 1000, 1),
                    success=ok,
                    offline=offline,
                )
            )


class TraceStepOut(BaseModel):
    name: str
    service: str
    duration_ms: float
    success: bool
    offline: bool = False


def trace_to_out(trace: Trace) -> list[TraceStepOut]:
    return [
        TraceStepOut(
            name=s.name, service=s.service, duration_ms=s.duration_ms, success=s.success, offline=s.offline
        )
        for s in trace.steps
    ]
