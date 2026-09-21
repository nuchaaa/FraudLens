# ADR-019: Leased local outbox delivery

Status: accepted, experimental local delivery, 2026-09-21.

Each committed outbox event has one delivery record, created atomically by a database
trigger (existing rows are backfilled). Event identity and payload remain immutable.
The initial destination is fixed: `local-recording-v1`. This is a single destination,
not fan-out; adding destinations requires per-destination delivery state and migration.

Workers claim due records using PostgreSQL `FOR UPDATE SKIP LOCKED`, database time,
a fresh UUID fencing token and a bounded lease. Each claim increments attempts, including
claims abandoned by a crashed worker. Claim transactions commit before handlers run.
Acknowledgement/failure requires the current unexpired token; stale workers cannot
acknowledge or reschedule another worker's claim. Expired claims become eligible again.
The dispatcher claims one event at a time within a bounded run, avoiding batches whose
leases expire while earlier handlers run. There is no heartbeat or forced handler timeout.

Failures retry with capped exponential backoff (5 seconds, doubling to 1 hour), up to
five claims by default. Exhaustion, including an expired final claim, becomes visible
dead-letter state. No automatic redrive or deletion is provided. Operators investigate
before a separately designed audited redrive. Only fixed error categories are retained;
exception messages may contain secrets and are not stored. CLI status exposes bounded
dead-letter identities plus aggregate counts; it prints no payloads.

Delivery is **at least once**, subject to bounded retries and operator recovery of dead
letters. A crash after handling but before acknowledgement causes redelivery. Fencing
protects queue state, not an external effect: an expired worker may still be handling.
Consumers must durably deduplicate `(consumer_id, event_id)` in the same transaction as
their local effect, or use a destination's idempotency key. Exactly-once external delivery
is not promised. Event ordering across workers/retries is not guaranteed.

The only shipped handler records an immutable PostgreSQL receipt, whose unique composite
key is both its local effect and deduplication record. It validates schema version 1 and
known event type; unknown versions fail and retry. Unreadable envelopes (including future
unknown event types) dead-letter as `unsupported_envelope` before handler invocation.
Receipt commit precedes queue ack.
It does not send notifications, run fraud actions, train models or authorize learning.
Future real consumers require explicit routing, schema compatibility and side-effect design.

Published outbox events and completed/dead delivery state are immutable. Receipt history
rejects updates/deletes/truncation. Existing database-owner bypass and least-privilege
deployment concerns remain. The worker is an explicit local database operator command,
never an unauthenticated HTTP endpoint or automatic API startup task.

All workers must use the same policy; changing policy is an operator change, not redrive.
Each claim scans at most 100 eligible records to retire expired exhausted claims; a run
with zero deliveries does not prove the backlog is empty. Status includes pending,
published, active/expired leases and dead counts, with at most 100 dead-letter details.
Legacy repository publication helpers serialize on delivery state and reject leased or
terminal records. Migration preserves legacy publication without inventing consumer receipts.

Rejected: holding the business transaction during delivery, in-memory retry counters,
unfenced acknowledgements, unbounded retries, claiming external exactly-once semantics,
and adding a broker before a concrete external destination exists.
