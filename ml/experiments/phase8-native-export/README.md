# Experimental native export verification

Seed17's reviewed Phase 7 XGBoost model was exported to native UBJSON without retraining.
All 2,400 stored feature rows matched exactly: maximum absolute score difference 0.0.
This is serialization/inference parity, not a new predictive-performance measurement.

The manifest and parity record are retained here; the native model and original report
live at ../../work/phase8/seed17 relative to repository root. No model is loaded by HTTP.
Trusted manifest SHA256:
`52ca9d5e967e39d8153e0a7b2b4ac593d647cb0046d3909dbb199cf05fd5d903`.

Local CLI replay also passed using ../../work/phase8/first-context.json hydrated from
the original synthetic source. See development.md for the exact command and ADR-014
for trust, scope and unknown-training-time limitations. production_eligible=false.
