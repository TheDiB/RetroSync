"""Interactive, non-destructive first-run configuration wizard.

No NAS writes, SSH enrollment, mount operations, or replacement of existing
configuration files are performed.
"""
import json
import os
from pathlib import Path


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
    remote_root = required("NAS saves root relative to mount [Save]: ") if False else ask("NAS saves root relative to mount [Save]: ").strip() or "Save"
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
    if not Path(nas["mount"]).is_absolute():
        raise ValueError("NAS mount must be an absolute path")
    if not Path(config["games"][0]["local_dir"]).is_absolute():
        raise ValueError("Local saves directory must be an absolute path")
    for value in (nas["remote_root"], config["games"][0]["remote_dir"]):
        p = Path(value)
        if p.is_absolute() or any(part in (".", "..") for part in value.replace("\\", "/").split("/")):
            raise ValueError("NAS-relative directories must not be absolute or contain . or ..")
    if "batocera" in config:
        from remote_activity import detect_batocera_retroarch
        # Reuse the existing detector's input validation without making an SSH call.
        # The detector rejects unsafe host/user before invoking its runner.
        class _NoNetwork:
            def __call__(self, *args, **kwargs):
                raise AssertionError("Setup validation must never connect")
        try:
            detect_batocera_retroarch(config["batocera"]["host"],
                                     user=config["batocera"]["user"], runner=_NoNetwork())
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid Batocera SSH endpoint: {exc}") from exc


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
    if ask("Create this new configuration file? [yes/NO]: ").strip().lower() != "yes":
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
