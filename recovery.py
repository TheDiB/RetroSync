"""Fixture-only incident inspection and non-destructive recovery export.

No automatic restore, NAS access, or integration with the sync CLI.
"""
import os
from pathlib import Path

from safe_copy import CopyPreconditionError, sha256, _require_regular_file


def inspect_fixture(destination, backup, expected_backup_sha256, expected_destination_sha256=None):
    """Report integrity without modifying any file. Expected hashes are trusted inputs."""
    destination, backup = Path(destination), Path(backup)
    if not _valid_digest(expected_backup_sha256):
        raise CopyPreconditionError("Valid expected backup SHA-256 required")
    if expected_destination_sha256 is not None and not _valid_digest(expected_destination_sha256):
        raise CopyPreconditionError("Invalid expected destination SHA-256")
    result = {"backup": str(backup), "destination": str(destination),
              "backup_status": "MISSING", "destination_status": "MISSING",
              "can_export_backup": False}
    if backup.is_symlink():
        result["backup_status"] = "UNSAFE_SYMLINK"
    elif backup.is_file():
        result["backup_status"] = ("VERIFIED" if sha256(backup) == expected_backup_sha256.lower()
                                   else "HASH_MISMATCH")
    if destination.is_symlink():
        result["destination_status"] = "UNSAFE_SYMLINK"
    elif destination.is_file():
        actual = sha256(destination)
        result["destination_status"] = ("PRESENT_UNVERIFIED" if expected_destination_sha256 is None
            else "MATCH" if actual == expected_destination_sha256.lower() else "HASH_MISMATCH")
    result["can_export_backup"] = result["backup_status"] == "VERIFIED"
    return result


def export_backup_fixture(backup, output, expected_backup_sha256):
    """Export verified backup to a NEW path, never replace an existing file.

    The output is a recovery candidate for manual review, NOT an automatic restore.
    Exclusive creation prevents overwriting an existing destination. No protection
    against concurrent mutation of the backup or filesystem power loss is claimed.
    """
    backup, output = Path(backup), Path(output)
    if not _valid_digest(expected_backup_sha256):
        raise CopyPreconditionError("Valid expected backup SHA-256 required")
    _require_regular_file(backup)
    if sha256(backup) != expected_backup_sha256.lower():
        raise CopyPreconditionError("Backup integrity mismatch")
    if output.is_symlink() or output.exists():
        raise CopyPreconditionError("Recovery output already exists")
    created = False
    try:
        with backup.open("rb") as src, output.open("xb") as dst:
            created = True
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                dst.write(chunk)
            dst.flush()
            os.fsync(dst.fileno())
        if sha256(output) != expected_backup_sha256.lower():
            raise CopyPreconditionError("Recovery export integrity mismatch")
        return {"output": str(output), "sha256": expected_backup_sha256.lower()}
    except Exception:
        if created:
            # The partial output remains for forensic inspection, never delete
            # an uncertain file or silently retry.
            pass
        raise


def _valid_digest(value):
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdefABCDEF" for c in value))
