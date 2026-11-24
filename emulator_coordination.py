"""Fixture-only admission protocol for cooperating emulator and sync callers."""
from contextlib import contextmanager

from execution_lock import local_execution_lock


@contextmanager
def fixture_admission(directory, role, *, detector):
    """Hold the same local lock for either role for the entire protected body.

    Caller must not launch or perform work unless admitted, and must finish
    all child activity before leaving the context. No production authority.
    """
    report = {"role": role, "status": "DEFERRED", "reason": "INVALID_ROLE",
              "write_authorized": False, "coordination_verified": False}
    if role not in ("emulator", "sync"):
        report["status"] = "BLOCKED"
        yield report
        return

    with local_execution_lock(directory) as lock:
        report["reason"] = lock["reason"]
        if lock["status"] == "ACQUIRED":
            try:
                status, detail = detector()
                if status not in ("RUNNING", "STOPPED", "UNKNOWN") or not isinstance(detail, str):
                    raise ValueError("Invalid detector response")
            except Exception:
                status = "UNKNOWN"
            if status == "STOPPED":
                report.update(status="ADMITTED", reason="LOCAL_FIXTURE_ADMITTED")
            elif status == "RUNNING":
                report["reason"] = "EMULATOR_RUNNING"
            else:
                report["reason"] = "EMULATOR_STATE_UNKNOWN"
        yield report
