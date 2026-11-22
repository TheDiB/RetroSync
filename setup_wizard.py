"""Interactive, non-destructive first-run configuration wizard.

No NAS writes, SSH enrollment, mount operations, or replacement of existing
configuration files are performed.
"""
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath


def build_config(ask=input, say=print):
    """Collect one game and an optional existing Batocera SSH endpoint."""
    def required(label):
        while True:
            value = ask(label).strip()
            if value:
                return value
            say("A nonempty value is required.")

    say("RetroSync setup | configuration only | no save writes")
    device_id = required("Device ID: ")
    mount = required("Existing NAS mount path: ")
    source = required("Expected CIFS source (//server/share): ")
    remote_root = ask("NAS saves root relative to mount [Save]: ").strip() or "Save"
    game_id = required("Game ID: ")
    filename = required("Game filename without extension: ")
    local_dir = required("Local saves directory: ")
    remote_dir = required("Game directory relative to NAS saves root: ")
    host = ask("Batocera SSH host (optional, blank to skip): ").strip()
    config = {
        "schema_version": 1,
        "device_id": device_id,
        "nas": {"mount": mount, "expected_source": source, "remote_root": remote_root},
        "games": [{"id": game_id, "filename": filename,
                   "local_dir": local_dir, "remote_dir": remote_dir}],
    }
    if host:
        user = ask("Batocera SSH user [root]: ").strip() or "root"
        config["batocera"] = {"host": host, "user": user}
    validate_setup_config(config)
    return config


def validate_setup_config(config):
    """Validate wizard-specific path and SSH safety constraints."""
    nas = config["nas"]
    if not nas["expected_source"].startswith("//") or len(nas["expected_source"].split("/")) < 4:
        raise ValueError("Expected CIFS source must look like //server/share")
    def absolute(value):
        return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()
    if not absolute(nas["mount"]):
        raise ValueError("NAS mount must be an absolute path")
    if not absolute(config["games"][0]["local_dir"]):
        raise ValueError("Local saves directory must be an absolute path")
    for value in (nas["remote_root"], config["games"][0]["remote_dir"]):
        p = Path(value)
        if absolute(value) or any(part in (".", "..") for part in value.replace("\\", "/").split("/")):
            raise ValueError("NAS-relative directories must not be absolute or contain . or ..")
    if "batocera" in config:
        from remote_activity import detect_batocera_retroarch
        class _NoNetwork:
            def __call__(self, *args, **kwargs):
                return type("Result", (), {"returncode": 255, "stdout": ""})()
        _, detail = detect_batocera_retroarch(
            config["batocera"]["host"], user=config["batocera"]["user"],
            runner=_NoNetwork())
        if detail.startswith("Invalid SSH"):
            raise ValueError(f"Invalid Batocera SSH endpoint: {detail}")


def run_setup(target, *, dry_run=False, ask=input, say=print):
    """Preview config and create it exclusively after explicit confirmation."""
    target = Path(target).expanduser()
    if target.exists() or target.is_symlink():
        say(f"REFUSED: configuration already exists: {target}")
        return 2
    config = build_config(ask=ask, say=say)
    payload = json.dumps(config, indent=2, ensure_ascii=False) + "\n"
    say(f"\nProposed configuration: {target}\n{payload}")
    if dry_run:
        say("DRY RUN: nothing written.")
        return 0
    if ask("Create this new configuration file? [y/yes/NO]: ").strip().lower() not in ("y", "yes"):
        say("Cancelled: nothing written.")
        return 0
    # Exclusive creation prevents overwriting a file created after the preview.
    # Parent directory must already exist: setup never modifies directory trees.
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(target, flags, 0o600)
    except FileExistsError:
        say(f"REFUSED: configuration appeared during setup: {target}")
        return 2
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
    except BaseException:
        try:
            target.unlink()
        except OSError:
            pass
        raise
    say(f"Created: {target} (no NAS or SSH changes)")
    return 0


def run_platform_preview(config, *, verify_mount, ask=input, say=print):
    """Interactively preview a platform inventory without changing configuration.

    NAS mount verification is mandatory before the remote directory is read.
    No config file or save is written.
    """
    from platform_discovery import discover_platform
    from platform_comparison import compare_platform
    from platform_report import render_platform_report

    nas = config["nas"]
    verify_mount(Path(nas["mount"]), nas["expected_source"])
    say("RetroSync platform preview | READ ONLY | no configuration changes")

    def required(prompt):
        value = ask(prompt).strip()
        if not value:
            raise ValueError(f"Required field missing: {prompt}")
        return value

    platform_id = required("Platform ID (e.g. gbc): ")
    local_dir = Path(required("Local platform saves directory (absolute): ")).expanduser()
    if not local_dir.is_absolute():
        raise ValueError("Local saves directory must be absolute")
    remote_dir = required("Remote platform directory relative to NAS saves root (e.g. gbc): ")
    if (PurePosixPath(remote_dir).is_absolute()
            or PureWindowsPath(remote_dir).is_absolute()
            or any(part in (".", "..", "") for part in remote_dir.replace("\\", "/").split("/"))):
        raise ValueError("Remote platform directory must be relative and traversal-free")
    local_emulator = ask("Local emulator [retroarch]: ").strip() or "retroarch"
    local_core = ask("Local core [unknown]: ").strip() or "unknown"
    remote_emulator = ask("Remote emulator [retroarch]: ").strip() or "retroarch"
    remote_core = ask("Remote core [unknown]: ").strip() or "unknown"
    remote_root = nas["remote_root"]
    if (not isinstance(remote_root, str) or not remote_root
            or PurePosixPath(remote_root).is_absolute()
            or PureWindowsPath(remote_root).is_absolute()
            or any(part in (".", "..", "") for part in remote_root.replace("\\\\", "/").split("/"))):
        raise ValueError("Invalid NAS remote_root")
    root = Path(nas["mount"]) / remote_root
    mapping = {
        "id": platform_id,
        "local": {"emulator": local_emulator, "core": local_core, "save_dir": str(local_dir)},
        "remote": {"emulator": remote_emulator, "core": remote_core,
                   "save_dir": str(root / remote_dir)},
    }
    report = discover_platform(mapping)
    say(json.dumps(report, indent=2, ensure_ascii=False))
    comparison = compare_platform(report)
    say("Platform comparison | exact filenames | READ ONLY")
    say(json.dumps(comparison, indent=2, ensure_ascii=False))
    say(render_platform_report(report, comparison))
    say("READ ONLY: no configuration or save files modified; compatibility not established.")
    return 0
