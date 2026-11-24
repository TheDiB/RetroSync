# Baseline initialization (v0.11.2)

A fresh full configured scan proposes history only for exact-name SRAM pairs with equal SHA-256. Divergent, missing and state files are excluded. Empty platform histories are valid. The timestamp records the observation, not a completed transfer.

Drafts retain schema v2 for read-only planner compatibility and add initialization metadata: method, mapping SHA-256 and provenance_verified=false. The fingerprint covers device ID, configured NAS mount/source/root and sorted platform endpoint paths, emulator and core names. Policy changes do not invalidate the mapping. This is a configuration binding, not authentication, physical endpoint identity or proof of game attribution.

Fixture persistence writes and fsyncs a temporary file, verifies bytes and schema, then publishes with an exclusive hard link to baseline-initialization.fixture.json. Existing targets are never replaced. Unsupported hard links fail closed. Caller must use an isolated test directory. Directory durability, hostile concurrent directory changes and production storage permissions are not established.

The draft builder is read-only; persistence is not connected to CLI or production history. Existing v2 readers can read the draft but cannot establish its provenance. No saved report or draft authorizes a transfer. Runtime coordination, trusted attribution and compatibility, and durable history management remain future work.
