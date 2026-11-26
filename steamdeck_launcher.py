"""Experimental Steam Deck launch adapter; not production authorization.

Only the observed Steam RetroArch launch profile is supported.
The internal runtime script must independently validate and acquire the lock.
"""
import os
import stat
import sys
from pathlib import Path, PurePosixPath


def build_runtime_command(argv, *, retroarch_dir, runtime_script):
    """Pure transformation of the supported Steam argv; no filesystem access."""
    directory = PurePosixPath(retroarch_dir)
    script = PurePosixPath(runtime_script)
    if (not directory.is_absolute() or not script.is_absolute()
            or ".." in directory.parts or ".." in script.parts
            or directory.parts[-3:] != ("steamapps", "common", "RetroArch")
            or script.name != "steamdeck_runtime.sh"):
        raise ValueError("Unsupported launcher paths")
    common = directory.parent
    steam = common.parent.parent
    expected = [
        str(steam / "steamrt64/steam-launch-wrapper"),
        "--oom-score-adjust", "900", "--",
        str(steam / "steamrt64/reaper"),
        "SteamLaunch", "AppId=1118310", "--",
        str(common / "SteamLinuxRuntime_sniper/_v2-entry-point"),
        "--verb=waitforexitandrun", "--",
        str(directory / "retroarch.sh"),
    ]
    if list(argv) != expected:
        raise ValueError("Unsupported Steam launch structure")
    return expected[:-1] + [str(script)]


def _private_owned(path, *, directory=False, executable=False):
    info = path.lstat()
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if (not kind(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077
            or (not directory and info.st_nlink != 1)
            or (executable and not info.st_mode & stat.S_IXUSR)):
        raise ValueError("Unsafe fixture path")


def main(argv=None):
    """Usage: python3 steamdeck_launcher.py FIXTURE_DIR -- %command%"""
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if sys.platform != "linux" or len(args) < 3 or args[1] != "--":
            raise ValueError("Expected Linux and FIXTURE_DIR -- Steam command")
        root = Path(args[0])
        if not root.is_absolute() or root.resolve(strict=True) != root:
            raise ValueError("Expected canonical fixture directory")
        _private_owned(root, directory=True)
        script = root / "steamdeck_runtime.sh"
        _private_owned(script, executable=True)
        _private_owned(root / "retrosync.lock")
        command = build_runtime_command(
            args[2:], retroarch_dir=os.getcwd(), runtime_script=str(script))
        os.execv(command[0], command)
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(f"RetroSync launcher blocked: {exc}", file=sys.stderr)
        return 125
    return 125


if __name__ == "__main__":
    sys.exit(main())
