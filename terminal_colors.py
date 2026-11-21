"""Minimal ANSI colors for human-readable terminal status labels."""

import os

_COLORS = {
    "PASS": "32",
    "FAIL": "31",
    "UNKNOWN": "33",
    "WARN": "33",
    "SKIP": "90",
}


def use_color(mode, stream, environ=None):
    """Respect CLI choice, redirected output, and NO_COLOR convention."""
    if mode == "always":
        return True
    if mode == "never":
        return False
    if mode != "auto":
        raise ValueError(f"Unsupported color mode: {mode}")
    env = os.environ if environ is None else environ
    return bool(getattr(stream, "isatty", lambda: False)()) and (
        "NO_COLOR" not in env and env.get("TERM", "") != "dumb"
    )


def colorize_status(status, enabled):
    """Color the bracketed label only, never the diagnostic detail."""
    label = f"[{status}]"
    if not enabled or status not in _COLORS:
        return label
    return f"\x1b[{_COLORS[status]}m{label}\x1b[0m"
