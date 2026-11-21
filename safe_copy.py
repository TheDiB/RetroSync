"""Experimental safe-copy primitive for isolated test fixtures only.

NOT connected to the RetroSync CLI or planner. This is not yet safe for
concurrent NAS writers, running emulators, or production save files.
"""
import hashlib
import os
import shutil
import tempfile
from pathlib import Path


class CopyPreconditionError(RuntimeError):
    pass


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _require_regular_file(path):
    if path.is_symlink() or not path.is_file():
        raise CopyPreconditionError(f"Not a regular non-symlink file: {path}")


def copy_fixture(source, destination, backup_dir, expected_source, expected_destination):
    """Copy test fixtures with verified backup and atomic destination replacement.

    The caller MUST provide an isolated test directory. A successful result
    does not imply remote locking, crash consistency, or concurrent-write safety.
    expected_* must be full SHA-256 strings from a prior inventory.
    """
    source, destination, backup_dir = map(Path, (source, destination, backup_dir))
    if source == destination or source.resolve() == destination.resolve():
        raise CopyPreconditionError("Source and destination must differ")
    _require_regular_file(source)
    _require_regular_file(destination)
    if not backup_dir.is_dir() or backup_dir.is_symlink():
        raise CopyPreconditionError("Backup directory must exist and not be a symlink")
    for expected in (expected_source, expected_destination):
        if not isinstance(expected, str) or len(expected) != 64 or any(
            c not in "0123456789abcdefABCDEF" for c in expected
        ):
            raise CopyPreconditionError("Full SHA-256 preconditions required")
    if sha256(source) != expected_source.lower() or sha256(destination) != expected_destination.lower():
        raise CopyPreconditionError("File changed since inventory")
    # The backup is written into a new unique file and verified before replace.
    # Backup and staging files are never left under the final destination name.
    backup_path = None
    staging_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=backup_dir, prefix="retrosync-backup-",
                                         suffix=".bak", delete=False) as tmp:
            backup_path = Path(tmp.name)
        shutil.copyfile(destination, backup_path)
        if sha256(backup_path) != expected_destination.lower():
            raise CopyPreconditionError("Backup integrity check failed")
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".retrosync-stage-",
                                         suffix=".tmp", delete=False) as tmp:
            staging_path = Path(tmp.name)
        shutil.copyfile(source, staging_path)
        if sha256(staging_path) != expected_source.lower():
            raise CopyPreconditionError("Staged copy integrity check failed")
        # Best-effort recheck, not a lock: concurrent changes can still race.
        if sha256(source) != expected_source.lower() or sha256(destination) != expected_destination.lower():
            raise CopyPreconditionError("File changed during staging")
        os.replace(staging_path, destination)
        staging_path = None
        if sha256(destination) != expected_source.lower():
            raise CopyPreconditionError("Post-replacement verification failed; restore backup manually")
        return {"backup": str(backup_path), "destination": str(destination),
                "sha256": expected_source.lower()}
    except Exception:
        # Keep a completed backup if replacement may have occurred; otherwise
        # do not delete it either, to simplify forensic recovery.
        raise
    finally:
        if staging_path is not None:
            staging_path.unlink(missing_ok=True)
