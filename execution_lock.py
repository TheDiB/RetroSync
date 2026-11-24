"""Local cooperative execution lock; never a write authorization.

Linux flock only. Caller supplies a private, trusted local fixture directory.
Never remove or replace the lock file, including after release.
"""
import errno
import os
import stat
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None


@contextmanager
def local_execution_lock(directory):
    result = {"status": "DEFERRED", "reason": "LOCK_UNAVAILABLE",
              "write_authorized": False, "coordination_verified": False}
    fd = None
    acquired = False
    try:
        if fcntl is None or not hasattr(os, "O_NOFOLLOW"):
            result["reason"] = "LOCK_UNSUPPORTED"
        else:
            try:
                root = Path(directory)
                if not root.is_absolute() or root.resolve(strict=True) != root:
                    raise ValueError("Expected canonical local fixture directory")
                info = root.stat()
                if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                        or info.st_mode & 0o077):
                    raise ValueError("Expected private owned directory")
                path = root / "retrosync.lock"
                fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW |
                             os.O_NONBLOCK, 0o600)
                info = os.fstat(fd)
                if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                        or info.st_uid != os.getuid() or info.st_mode & 0o077):
                    raise ValueError("Unsafe lock file")
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    if exc.errno in (errno.EACCES, errno.EAGAIN):
                        result["reason"] = "LOCK_BUSY"
                    else:
                        raise
                else:
                    current = path.lstat()
                    if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
                        raise ValueError("Lock path changed")
                    acquired = True
                    result.update(status="ACQUIRED", reason="LOCAL_LOCK_ACQUIRED")
            except (OSError, ValueError, TypeError, RuntimeError):
                result["reason"] = "LOCK_UNAVAILABLE"
        yield result
    finally:
        if fd is not None:
            # Closing releases the kernel lock when no inherited descriptor remains.
            # Never unlink: another process may already have opened the same inode.
            os.close(fd)
