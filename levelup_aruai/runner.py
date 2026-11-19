"""Runs small Python snippets: captures their output and traces them line by line.

Both agents rely on this. The Question Agent runs every snippet to get the true
answer (so an answer key can never be wrong), and the Teacher Agent uses the
trace to walk the learner through what happened, step by step.
"""
from __future__ import annotations

import contextlib
import io
import sys
from dataclasses import dataclass, field

FILENAME = "<levelup>"
MAX_STEPS = 60
_SIMPLE = (int, float, str, bool, list, tuple, dict, set, type(None))


@dataclass
class TraceStep:
    line: int
    source: str
    variables: dict[str, str]  # variable name -> repr, as the line is about to run
    scope: str = "main"


@dataclass
class RunResult:
    output: str
    error: str | None = None
    steps: list[TraceStep] = field(default_factory=list)
    final_variables: dict[str, str] = field(default_factory=dict)
    truncated: bool = False


def _snapshot(namespace: dict) -> dict[str, str]:
    snap = {}
    for name, value in namespace.items():
        if name.startswith("__") or not isinstance(value, _SIMPLE):
            continue
        text = repr(value)
        snap[name] = text if len(text) <= 60 else text[:57] + "..."
    return snap


def run_snippet(code: str, trace: bool = False) -> RunResult:
    """Execute ``code`` and return its printed output (trailing whitespace stripped)."""
    lines = code.splitlines()
    steps: list[TraceStep] = []
    state = {"truncated": False}

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != FILENAME:
            return None
        if event == "line":
            if len(steps) >= MAX_STEPS:
                state["truncated"] = True
                return tracer
            n = frame.f_lineno
            scope = frame.f_code.co_name
            steps.append(
                TraceStep(
                    line=n,
                    source=lines[n - 1].strip() if 0 < n <= len(lines) else "",
                    variables=_snapshot(frame.f_locals),
                    scope="main" if scope == "<module>" else scope,
                )
            )
        return tracer

    namespace: dict = {"__name__": "__levelup__"}
    buf = io.StringIO()
    error = None
    compiled = compile(code, FILENAME, "exec")
    old_trace = sys.gettrace()
    try:
        with contextlib.redirect_stdout(buf):
            if trace:
                sys.settrace(tracer)
            try:
                exec(compiled, namespace)  # noqa: S102 - code comes from our own templates
            finally:
                if trace:
                    sys.settrace(old_trace)
    except Exception as exc:  # report errors as data, the Teacher explains them
        error = f"{type(exc).__name__}: {exc}"
    return RunResult(
        output=buf.getvalue().rstrip(),
        error=error,
        steps=steps,
        final_variables=_snapshot(namespace),
        truncated=state["truncated"],
    )
