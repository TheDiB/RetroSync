"""Read-only environment checks. A PASS is not permission to write saves.

Remote Batocera RetroArch detection is optional and advisory. A process
snapshot cannot guarantee that no other NAS client is writing saves.
"""
import os
import sys
from pathlib import Path

from remote_activity import detect_batocera_retroarch


def detect_retroarch(proc_root=Path("/proc"), platform=None):
    """Return (status, details): RUNNING, STOPPED, or UNKNOWN.

    Inspect Linux process comm and executable argv[0], not arbitrary command
    arguments (which could mention retroarch without running it).
    """
    platform = sys.platform if platform is None else platform
    if not platform.startswith("linux"):
        return "UNKNOWN", "Process detection is implemented only for Linux"
    try:
        pids = [p for p in proc_root.iterdir() if p.name.isdigit() and p.is_dir()]
    except OSError as exc:
        return "UNKNOWN", f"Cannot inspect process table: {exc}"
    found = []
    unreadable = 0
    for pid in pids:
        try:
            comm = (pid / "comm").read_text(encoding="utf-8").strip().lower()
            argv = (pid / "cmdline").read_bytes().split(b"\0")
            executable = os.path.basename(os.fsdecode(argv[0])).lower() if argv and argv[0] else ""
            if comm in ("retroarch", "retroarch.exe") or executable in ("retroarch", "retroarch.exe"):
                found.append(pid.name)
        except (OSError, UnicodeError):
            # A process may disappear during enumeration. Never claim certainty
            # if its identity could not be inspected.
            unreadable += 1
    if found:
        return "RUNNING", f"RetroArch process PID(s): {', '.join(sorted(found))}"
    if unreadable:
        return "UNKNOWN", f"Could not inspect {unreadable} process(es)"
    return "STOPPED", "No local RetroArch process detected"


def preflight(config, check_mount_fn, proc_root=Path("/proc"), platform=None,
              remote_detector=None):
    """Collect checks without changing files or mounts."""
    checks = []

    def add(name, status, detail):
        checks.append({"name": name, "status": status, "detail": detail})

    if not isinstance(config, dict) or config.get("schema_version") != 1:
        add("config", "FAIL", "Unsupported configuration schema")
        return checks
    try:
        nas = config["nas"]
        games = config["games"]
        mount = Path(nas["mount"])
        source = nas["expected_source"]
        root = mount / nas["remote_root"]
        if not isinstance(games, list) or not games:
            raise ValueError("games must be a nonempty list")
        for game in games:
            for field in ("id", "filename", "local_dir", "remote_dir"):
                if not isinstance(game[field], str) or not game[field]:
                    raise ValueError(f"Invalid game field: {field}")
    except (KeyError, TypeError, ValueError) as exc:
        add("config", "FAIL", f"Invalid configuration: {exc}")
        return checks
    batocera = config.get("batocera")
    if batocera is not None:
        if not isinstance(batocera, dict) or not isinstance(batocera.get("host"), str) or not batocera["host"]:
            add("config", "FAIL", "Invalid Batocera SSH configuration: host is required")
            return checks
        if not isinstance(batocera.get("user", "root"), str) or not batocera.get("user", "root"):
            add("config", "FAIL", "Invalid Batocera SSH configuration: user must be a string")
            return checks
    add("config", "PASS", f"{len(games)} game(s) configured")
    try:
        check_mount_fn(mount, source)
        add("nas_mount", "PASS", f"Expected CIFS source mounted at {mount}")
        mounted = True
    except (OSError, RuntimeError, ValueError) as exc:
        add("nas_mount", "FAIL", str(exc))
        mounted = False
    for game in games:
        local = Path(game["local_dir"])
        add(f"local:{game['id']}", "PASS" if local.is_dir() else "FAIL",
            f"Directory {'accessible' if local.is_dir() else 'missing'}: {local}")
        remote = root / game["remote_dir"]
        if not mounted:
            add(f"remote:{game['id']}", "SKIP", "NAS mount check failed")
        else:
            add(f"remote:{game['id']}", "PASS" if remote.is_dir() else "FAIL",
                f"Directory {'accessible' if remote.is_dir() else 'missing'}: {remote}")
    status, detail = detect_retroarch(proc_root, platform)
    add("retroarch_local", {"RUNNING": "FAIL", "STOPPED": "PASS",
                             "UNKNOWN": "UNKNOWN"}[status], detail)
    if batocera is None:
        add("remote_emulator_activity", "UNKNOWN",
            "Batocera SSH is not configured; other NAS clients cannot be checked")
    else:
        detector = detect_batocera_retroarch if remote_detector is None else remote_detector
        try:
            remote_status, remote_detail = detector(batocera["host"], user=batocera.get("user", "root"))
        except Exception as exc:
            # Fail closed even if an injected detector unexpectedly fails.
            remote_status, remote_detail = "UNKNOWN", f"Remote inspection error: {type(exc).__name__}"
        if remote_status not in ("RUNNING", "STOPPED", "UNKNOWN"):
            remote_status, remote_detail = "UNKNOWN", "Invalid remote inspection status"
        add("remote_emulator_activity",
            {"RUNNING": "FAIL", "STOPPED": "PASS", "UNKNOWN": "UNKNOWN"}[remote_status],
            f"{remote_detail} (RetroArch only; snapshot, not write authorization)")
    return checks


def check_exit_code(checks):
    """Nonzero for blocking failures; remote-client uncertainty is advisory."""
    return 2 if any(c["status"] in ("FAIL", "SKIP") or
                    (c["status"] == "UNKNOWN" and c["name"] != "remote_emulator_activity")
                    for c in checks) else 0
