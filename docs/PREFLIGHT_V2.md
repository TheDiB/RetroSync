# Preliminary preflight (v0.11.3a)

The independent preflight_v2 API returns structured checks and READY, DEFERRED or BLOCKED. BLOCKED takes precedence. READY means preliminary observations passed, never permission to write.

Validate all configured mappings, reject unsupported emulators and malformed SSH settings, verify the NAS mount, observe endpoint identities and reject overlaps, inspect local and configured Batocera RetroArch activity, then recheck mount and endpoint identities. Unknown activity and absent remote inspection defer. Mount verification failures (including unexpected sources) defer conservatively; endpoint validation errors block, OS availability errors defer.

The mount adapter follows the existing raise-on-failure contract. No inventory hashing, lock acquisition, baseline mutation or save transfer is performed. Existing v1 CLI behavior is unchanged; v2 CLI integration is deferred. Tests inject adapters for portability.

Process snapshots do not prevent emulator launches or exclude other NAS writers. A configured Batocera host is not proof that it owns the remote endpoint. Endpoint observations are not leases; nested mounts and durable storage identity need further verification. Unknown cores and attribution remain unverified. All authorization, coordination, compatibility, attribution and provenance flags remain false even on READY. Do not use a serialized report as a capability. Subsequent milestones must establish coordination and revalidate under it.
