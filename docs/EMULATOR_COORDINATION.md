# Emulator coordination (v0.11.3c prototype)

The fixture_admission context manager accepts role emulator or sync and a
runtime detector returning (RUNNING|STOPPED|UNKNOWN, detail string).
Both roles acquire the same local execution lock before calling the detector.
Only STOPPED under the lock yields ADMITTED. Contention skips the detector.
Unknown, malformed or failed inspection defers; invalid roles are blocked.

ADMITTED means only that this cooperative local fixture may enter its
protected body. It is not production authorization. Both write_authorized
and coordination_verified remain false. Reports are diagnostic, not tokens.
Callers must check admission and keep the context open throughout activity.
Use a trusted private local fixture directory, never a save directory or NAS.
See EXECUTION_LOCK.md for filesystem and descriptor assumptions.

Tests simulate both roles with independent Python processes and verify
mutual exclusion in both directions, normal release and detector failures.
No real emulator is launched and no production files are modified.

## Future launcher requirements

A real launcher must cover the entire lifetime of every relevant writer,
including descendants and delayed save flushes. A wrapper that dies while
its emulator child survives cannot provide this guarantee with the current
lock API. Do not deploy this prototype as a real launcher. Investigate
process supervision or safe lock ownership transfer before integration.
Direct launches bypassing the protocol remain uncoordinated.

Steam Deck and Batocera require separate verified launch integration.
A remote process snapshot or an SSH connection alone is not a remote lease.
Network loss, remote process survival, other NAS clients, and recovery
after uncertain operations must fail closed. No distributed protocol,
production CLI integration, save transfer or history update is implemented.
