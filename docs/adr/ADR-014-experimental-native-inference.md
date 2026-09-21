# ADR-014: Explicitly experimental native model inference

Status: accepted, Phase 8 checkpoint, 2026-09-21.

## Decision

Implement FraudModel using ExperimentalXGBoostModel in infrastructure and a pure
captured-context service in backend/app/fraud. The API still loads no model. Local
replay returns an uncalibrated score, actual inference timestamp and exact model/feature
versions; it creates no assessment, decision, case, profile update or database write.

Only the three reviewed Phase 7 synthetic XGBoost artifacts are eligible for the export
tool. Their report SHA256 values are pinned in export_model.py independently of input
files. Verify the report first, then its original model and prepared-feature hashes.
Only those verified bytes are deserialized from memory, eliminating a path reread after
verification. This exporter is an offline migration tool, not an arbitrary pickle loader.
Future training runs require a separate review and extension of the allowed provenance.

Export the model to native UBJSON. Check native predictions against the original model
on all saved feature rows with absolute tolerance 1e-7; labels are not evaluated or used
to tune anything. Native inference never imports joblib/pickle or the offline ml package.
This follows [XGBoost model IO guidance](https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html).
Native parsing still requires trusted artifacts; it is not a sandbox for hostile models.

## Manifest, scope and trust

The strict versioned manifest binds native model SHA256, content-derived model version,
exact behavior-v1 feature order, full training-report hash, source-data/lock/original
pickle hashes, seed, XGBoost version and export timestamp. All flags remain CANDIDATE,
synthetic_only=true, production_eligible=false, calibrated=false. Files have fixed names;
metadata is bounded to 128 KiB and models to 32 MiB. Export directories are create-only;
manifest is written last. Report and model bytes are verified before native loading.

The loader requires an independently supplied trusted manifest digest (for example the
output of the reviewed local export). A checksum is not a signature or proof of source
legitimacy. Computing the expected digest from a newly received untrusted bundle does
not establish trust. Check exact runtime version, model shape and binary-logistic objective.
Reject changed or incompatible feature versions/order and non-finite/out-of-range outputs.
No fallback to a default model, zero score or fabricated prediction is allowed.

The context service limits this initial artifact to KZT, UTC profile policy and original
180/30-day windows. The low-level FraudModel port takes numeric vectors, so callers must
use the context service to enforce currency/policy scope. This scope check does not prove
that arbitrary inputs resemble the training distribution. ULB PCA inputs remain incompatible.

## Honest provenance and output semantics

Legacy reports lack an exact trained_at timestamp. Preserve trained_at=null and record
only the actual exported_at timestamp. Do not use file modification times or export time
as training time. No database ModelVersion is created, since its current required trained_at
cannot be truthfully populated for these legacy artifacts. Later durable registration
must model this explicitly or use a newly timestamped training run; never invent history.

FraudPrediction retains its existing internal field name probability for compatibility.
The public local report calls it uncalibrated_score and includes explicit experiment flags.
It is neither a calibrated fraud probability nor a customer verdict. Inference timestamp
is now, not a reconstructed historical decision time. It cannot precede context capture.
Scores/versions replay; the current inference timestamp intentionally changes each run.

## Verification and remaining integration

Seed17 native export matches all 2,400 saved feature rows exactly (max absolute difference
0.0). A real local CLI replay uses a context hydrated from the original saved synthetic
source. Tests cover port parity, corruption, provenance, scope, incompatible features,
model shape, invalid output, timestamp ordering, create-only exports, independent pins
before deserialization and database-free CLI failure handling.

Production validity, human authentication, HTTP inference and atomic durable evaluation
are not added. Phase 9 must define rule score/missingness semantics and experimental
risk policy explicitly before composing existing strategies; it must not manufacture
model provenance or automatically mutate immutable RECEIVED transactions.
