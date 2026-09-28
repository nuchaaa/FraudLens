# Local five-story demonstration

This is a **synthetic research demonstration**, not a fraud-performance result.
Use a disposable PostgreSQL `*_test` database on a local Unix socket. Start the
backend/frontend with the local settings in `development.md`; never use these
instructions against real customer data or a remote service.

1. Preview `.venv/bin/python -m backend.adapters.demo` and inspect
   `.venv/bin/python -m backend.adapters.demo --manifest`. The fixed manifest
   lists every customer/transaction UUID, timestamp and authored story. Its
   SHA-256 is `4645220dd30cfabb12e8a22688a45035d81e352fe2ef5998f6f16a33019f26c8`.
2. Set `TEST_DATABASE_URL` to the disposable socket URL from `development.md`.
   For a quick facts-only worklist, explicitly run
   `.venv/bin/python -m backend.adapters.demo --apply`. A rerun
   replays the same transactions. The seeder uses a synthetic admin fixture
   actor and creates only customer/transaction, audit, outbox and idempotency
   rows. It does not log in as a real person.
   Run `.venv/bin/python -m backend.adapters.demo --progress` at any point to
   inspect the **read-only** evidence ledger. It reports `ABSENT`, `MATCH` or
   `CONFLICT` for each fixture fact; recorded evaluation IDs and captured profile
   versions; case state and feedback; learning action/reason; and each immutable
   profile revision's count, median and admitted fixture IDs. It refuses a
   non-disposable database just like `--apply`. A `CONFLICT` means stop: the
   stable fixture ID already points to different facts.
   For a concise presenter view, run
   `.venv/bin/python -m backend.adapters.demo --walkthrough`. It uses the same
   read-only snapshot and guard, shows the 14 candidate transfers by story,
   recorded risk status/case/feedback counts, the current profile version and
   the next manual step. It never supplies a verdict. On the current working
   test DB, it reports **49 matching facts and 13 absent candidates**, with no
   profile revisions. Story A has a retained rules-only INSUFFICIENT_EVIDENCE
   result; that is not a legitimate verdict.
   For a **sequenced demonstration**, use `--apply-stage` instead of bulk
   `--apply`. Start with
   `.venv/bin/python -m backend.adapters.demo --apply-stage BASELINE` (48
   unreviewed background transfers), then `--apply-stage A`. The command
   supports `B`, `C`, `D1`–`D5`, and `E1`–`E6` as later stages. It reuses the
   original manifest IDs and idempotency keys. Each invocation inserts facts
   only; replays are safe. B/C/D/E require a verified prior KZT profile whose
   original accepted bootstrap admitted at least five matching fixture
   background facts with two distinct recorded reviewers. An unrelated verified
   profile does not unlock these stages. This is stored workflow provenance,
   not independent proof of reviewer identity or external legitimacy. C also
   requires a retained B evaluation and a separate B learning decision that
   quarantined the exceptional legitimate amount without advancing the profile.
   Each later D stage requires its predecessor's separately authorized ACCEPT;
   each later E stage requires its predecessor's retained evaluation. The
   command refuses baseline backfill after a profile/candidate and earlier
   candidate insertion after later customer facts. It never creates the needed
   reviews or gate decisions for you. If the independent evidence is absent,
   stop at the current stage and show it as pending.
   `.venv/bin/python -m backend.adapters.demo --check-stage B` previews one
   stage without writing. It reports `READY`, `BLOCKED` with the missing
   prerequisite, `CONFLICT` for an incompatible fixture ID, or `REPLAYABLE` for
   an exact existing stage. This snapshot is not a reservation: `--apply-stage`
   checks prerequisites again immediately before inserting facts.
3. After bulk seeding on a fresh database, open the local analyst console and
   inspect the transaction worklist. All 62 records are initially **not evaluated**;
   staged seeding displays only the stages already inserted. The B
   vehicle payment is 8M KZT; C is a later 500k transfer by the same customer
   to a new recipient. D and E contain the authored progression sequences.
   The `BC` rows are the shared prior history for B and C.
4. If experimental routes are enabled locally, evaluate any transaction with
   an explicit absent profile: `POST /api/v1/experimental/evaluations`, an
   `Idempotency-Key`, and a body such as
   `{"transaction_id":"<manifest UUID>","profile_version":null,"strategy":"rules_only","manifest_sha256":null}`.
   Inspect the returned evidence. Missing admitted history may produce
   **INSUFFICIENT EVIDENCE**; do not present it as a low-risk verdict.
5. A trustworthy profile demonstration needs actual authorized review inputs.
   Use the case/review routes with distinct local analyst identities, then the
   independent admin bootstrap route only for cases genuinely reviewed as
   legitimate. Bootstrap requires 5–100 closed legitimate cases, at least two
   reviewers and evaluations captured with absent profiles. Preserve the
   version returned before each later evaluation. Never copy the fixture's
   story text into a verdict automatically. The captured transaction has no
   merchant name, building or location field. An amount that looks small is
   not proof of legitimacy. If independent reviewers cannot verify the facts,
   record NEEDS_INVESTIGATION and leave bootstrap and later gated stages pending.
   A public business registry may verify registration of an already identified
   payee, but it cannot establish which business received a synthetic transfer.
   Do not attach a real Kazakhstan business or ИП to these authored transactions.
   Future payment context needs a transaction-linked source, source/observation
   provenance and an explicit unavailable state when a field was not supplied.
6. Only after a verified baseline exists, evaluate B against that pinned
   version. If independently confirmed legitimate, its exceptional amount
   should be handled by the conservative profile-learning gate; inspect the
   recorded decision rather than assuming an outcome. Evaluate C against the
   pre-decision version and compare the retained baseline. For D, review and
   apply each step in chronological order, pinning the current version each
   time. For E, preserve every review and gate decision; the authored attack
   story alone is not evidence that any transfer is fraudulent.

The progress ledger supports five specific checks, each conditional on **actual
stored reviewer and learning evidence**:

| Story | Evidence to inspect | What is still not proven |
| --- | --- | --- |
| A, normal-looking | The evaluation's captured profile version, case and any analyst feedback | Appearance or a quiet rule result is not a legitimate verdict. |
| B, exceptional vehicle purchase | A prior verified BC profile revision; a closed independently reviewed case; the gate's recorded action/reason; unchanged version/median and absence of B's ID from admitted observations if quarantined | Authored "vehicle" text is not proof that the purchase was legitimate. |
| C, later new recipient | Its own evaluation must name the intended pre-decision BC profile version; compare that revision with B's recorded learning decision | Today's revision list proves event-time fit only, not that the version existed before the original decision. |
| D, gradual change | Separate reviews and gate decisions in event order; an `ACCEPT` with advancing versions and the medians in those committed revisions | Five authored transfers alone do not prove legitimate concept drift or safe adaptation. |
| E, escalation | Retained evaluation and sequence evidence, reviewer findings and gate decisions for each transfer | The authored attack narrative is not a verified fraud label or detection-rate result. |

If review evidence is missing, present the step as pending. Never manually edit
profile or feedback tables to complete the story. `--progress` records what is
stored; it does not certify the human identity or external legitimacy evidence
behind a review.

No step executes a banking action. The model, rules, sequence signals and gate
thresholds are experimental and uncalibrated. A successful scripted demo does
not establish real-world fraud detection, false-positive rate or safe adaptation.
All old event timestamps are inserted at demo time; they do not reconstruct
historical arrival or knowledge time.
Even staged insertion only controls this local demonstration's insertion order.
It does not prove when a real bank would have received the facts or known the
review outcome. Bulk `--apply` deliberately bypasses stage prerequisites and
must not be described as a staged point-in-time run.
The local human-auth flow and current Compose setup are not approved for remote
exposure; Phase 15 release gates remain open.
