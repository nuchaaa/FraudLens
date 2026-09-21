# Native explanation numerical verification

The original pinned seed17 native model explained all 2,400 hash-verified prepared vectors.
verification.json records reconstruction errors and fixed tolerances, not fraud metrics.
No labels, retraining or selection/tuning were used. Original artifacts are unchanged.

Native margin reconstruction maximum absolute difference: 2.2863969206809998e-6.
Stable sigmoid versus native score maximum difference: 8.22891939034065e-8.
Both pass explanation-v1-experimental tolerances. This does not validate real-world risk,
causal interpretation or a second independent SHAP implementation.

Actual CLI replay is retained outside Git at ../../work/phase10/treeshap-seed17/replay.json
(relative to repository root). The hybrid result correctly abstains on missing raw history
while explaining the synthetic model component. See ADR-016 and development.md.
