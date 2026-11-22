"""Read-only Batocera RetroArch detection via SSH.

This is advisory and cannot authorize a synchronization write. It detects
RetroArch only, not every emulator or concurrent NAS writer.
"""
import re
import subprocess

_PID_LINE = re.compile(r"^\s*([0-9]+)\s+(\S+)\s*$")
_REMOTE_COMMAND = "ps -eo pid=,comm="


def parse_process_list(output):
    """Parse an entire ps listing; reject incomplete/unexpected output."""
    if not isinstance(output, str) or not output.strip():
        return "UNKNOWN", "Empty remote process list"
    pids = []
    seen = 0
    for line in output.splitlines():
        if not line.strip():
            continue
        match = _PID_LINE.fullmatch(line)
        if not match:
            return "UNKNOWN", "Unrecognized remote process listing"
        seen += 1
        if match.group(2).lower() in ("retroarch", "retroarch.exe"):
            pids.append(match.group(1))
    if not seen:
        return "UNKNOWN", "No process records"
    if pids:
        return "RUNNING", f"Remote RetroArch PID(s): {', '.join(pids)}"
    return "STOPPED", "No remote RetroArch process detected (other emulators not checked)"


def detect_batocera_retroarch(host, *, user="root", timeout=8, runner=None):
    """Query a trusted SSH host, without shell interpolation of host or user.

    SSH keys/known_hosts must be configured externally. Host must be an IPv4
    address or DNS hostname; SSH options and arbitrary targets are rejected.
    """
    if not isinstance(host, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}", host):
        return "UNKNOWN", "Invalid SSH hostname"
    if not isinstance(user, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,31}", user):
        return "UNKNOWN", "Invalid SSH username"
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
        return "UNKNOWN", "Invalid SSH timeout"
    run = subprocess.run if runner is None else runner
    command = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
               "-o", "ConnectTimeout=5", "-o", "NumberOfPasswordPrompts=0",
               "--", f"{user}@{host}", _REMOTE_COMMAND]
    try:
        result = run(command, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "UNKNOWN", f"SSH unavailable: {type(exc).__name__}"
    if result.returncode != 0:
        return "UNKNOWN", f"SSH/process inspection failed (exit {result.returncode})"
    return parse_process_list(result.stdout)
