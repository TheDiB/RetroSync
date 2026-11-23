"""Bounded, read-only platform save discovery (experimental v0.9).

No filesystem writes, NAS mounting, SSH calls, or compatibility assumptions.
The caller must verify the NAS mount independently before scanning it.
"""
import hashlib
import os
import re
import stat
from pathlib import Path

_STATE = re.compile(r"^(?P<stem>.+)\.state(?P<slot>[0-9]*)$", re.IGNORECASE)


def classify_save(filename):
    """Return (kind, slot) or None. Slot 0 denotes unsuffixed .state."""
    if filename.lower().endswith(".srm") and len(filename) > 4:
        return "SRAM", None
    match = _STATE.fullmatch(filename)
    if match:
        return "STATE", int(match.group("slot") or "0")
    return None


def _hash_file(path, before):
    h = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) != (
                before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
            raise RuntimeError("File changed before hashing")
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            h.update(block)
        after = os.fstat(stream.fileno())
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise RuntimeError("File changed during hashing")
    return h.hexdigest()


def scan_directory(root, *, max_entries=10000, max_bytes=1024 * 1024 * 1024):
    """Scan direct children only; fail closed on any incomplete scan.

    Does not follow symbolic links. A bounded scan avoids accidentally
    walking huge or unrelated directory trees. Results are deterministic.
    """
    root = Path(root)
    if max_entries < 1 or max_bytes < 1:
        raise ValueError("Scan limits must be positive")
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError(f"Missing, invalid, or symlinked directory: {root}")
    files = []
    count = 0
    with os.scandir(root) as entries:
        for entry in entries:
            count += 1
            if count > max_entries:
                raise RuntimeError(f"Scan limit exceeded: {max_entries} entries")
            if entry.is_symlink():
                raise RuntimeError(f"Symlink encountered: {entry.name}")
            if entry.is_dir(follow_symlinks=False):
                raise RuntimeError(f"Subdirectory requires explicit mapping: {entry.name}")
            if not entry.is_file(follow_symlinks=False):
                raise RuntimeError(f"Unsupported directory entry: {entry.name}")
            kind = classify_save(entry.name)
            if kind is None:
                continue
            # Windows DirEntry.stat may omit device and inode identifiers.
            # Obtain fresh path metadata comparable to os.fstat on all hosts.
            path = root / entry.name
            before = os.stat(path, follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode):
                raise RuntimeError(f"Not a regular file: {entry.name}")
            if before.st_size > max_bytes:
                raise RuntimeError(f"File size limit exceeded: {entry.name}")
            digest = _hash_file(path, before)
            files.append({"name": entry.name, "relative_path": entry.name,
                          "kind": kind[0], "slot": kind[1],
                          "bytes": before.st_size, "mtime_ns": before.st_mtime_ns,
                          "sha256": digest})
    files.sort(key=lambda item: item["relative_path"])
    return files


def discover_platform(mapping, *, max_entries=10000, max_bytes=1024 * 1024 * 1024):
    """Inventory both endpoints; core is declared, never inferred from names.

    Mapping: {id, local:{emulator,core,save_dir},
                 remote:{emulator,core,save_dir}}.
    This is an experimental input contract, NOT config schema v1.
    """
    if not isinstance(mapping, dict) or not isinstance(mapping.get("id"), str) or not mapping["id"]:
        raise ValueError("Platform id is required")
    output = {"platform": mapping["id"], "complete": False, "endpoints": {}}
    for side in ("local", "remote"):
        endpoint = mapping.get(side)
        if not isinstance(endpoint, dict):
            raise ValueError(f"Missing {side} endpoint")
        for key in ("emulator", "core", "save_dir"):
            if not isinstance(endpoint.get(key), str) or not endpoint[key]:
                raise ValueError(f"Invalid {side}.{key}")
        files = scan_directory(endpoint["save_dir"],
                               max_entries=max_entries, max_bytes=max_bytes)
        output["endpoints"][side] = {
            "emulator": endpoint["emulator"], "core": endpoint["core"],
            "save_dir": endpoint["save_dir"], "files": files}
    output["complete"] = True
    return output
