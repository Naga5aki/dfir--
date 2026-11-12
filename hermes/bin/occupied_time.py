#!/usr/bin/env python
"""Contrast tool for long interactive sessions. Not a pass/fail gate.

A gap counts as user idle only when it is strictly longer than five minutes
and the next message is from the user. Tool waits and model generation do not.
"""


def user_idle_seconds(messages: list[tuple[float, str]], gap: float = 300) -> float:
    idle = 0.0
    for (prev_ts, _), (ts, role) in zip(messages, messages[1:]):
        delta = ts - prev_ts
        if role == "user" and delta > gap:
            idle += delta
    return idle
