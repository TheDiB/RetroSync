# Local execution lock (v0.11.3b)

Experimental fixture-only API: `execution_lock.local_execution_lock(directory)`.
Use a canonical absolute, existing, private (0700), user-owned directory on a
trusted local Linux filesystem, outside save directories. All participating
instances must use the same directory and persistent retrosync.lock inode.

The context manager yields ACQUIRED / LOCAL_LOCK_ACQUIRED or DEFERRED with
LOCK_BUSY, LOCK_UNAVAILABLE or LOCK_UNSUPPORTED. Only enter the protected
operation on ACQUIRED, and only within the context. The returned dictionary
is diagnostic, not a capability. Both write_authorized and
coordination_verified remain false. No CLI or production transfer integration.

Linux flock uses exclusive nonblocking acquisition. Closing the descriptor
releases the lock when the last reference to its open file description closes.
Do not fork while holding the lock or pass the descriptor to other processes.
Never unlink, rename or replace the lock file, even after release or a crash.
No PID-based stale lock cleanup. The lock file contains no save data.

The caller must ensure the directory and its ancestors are trusted and stable,
and the filesystem is local. The implementation does not verify filesystem
type or defend against a same-user process replacing the directory or inode.
Do not use on CIFS/SMB/NFS. Distributed locking, mount identity, remote writers,
emulator launch prevention and transaction recovery remain separate problems.
Windows returns LOCK_UNSUPPORTED; no fallback to an unsafe sentinel file.

Tests use temporary directories, real independent processes and forced process
termination. A released lock does not imply an interrupted transaction is safe
to retry. Reconciliation must precede future production retries.
