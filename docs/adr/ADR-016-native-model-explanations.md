# ADR-016: Native TreeSHAP model explanations

Status: accepted, Phase 10 experimental checkpoint, 2026-09-21.

## Context and choice

The reviewed synthetic binary-logistic XGBoost gbtree is already pinned and loaded using
native UBJSON. Phase 9 retains the exact feature vector and model identity. There was no
implemented explanation contract; the module contained only a placeholder README.

Use XGBoost's native TreeSHAP implementation with pred_contribs=True,
approx_contribs=False, strict_shape=True, training=False and all trees. No new dependency,
training, arbitrary pickle, background dataset sampling or model export is required.
The ExplainableFraudModel port extends prediction with explain(FeatureVector). Infrastructure
owns native calls; domain contracts and readable composition remain framework-free.

Primary documentation checked against installed XGBoost 3.2.0's predict docstring:
[XGBoost 3.2 API](https://xgboost.readthedocs.io/en/release_3.2.0/python/python_api.html#xgboost.Booster.predict)
and [SHAP TreeExplainer](https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html).
The release documentation currently labels itself 3.2.1; runtime remains exactly pinned
3.2.0 by the existing manifest. Native pred_contribs returns feature attributions plus a
final bias term; their sum reconstructs the untransformed margin. Tree-path explanations
use model-internal path statistics rather than a newly selected background dataset.

Alternative: adding the shap package and an interventional background requires additional
reference-data/provenance and dependency decisions. That output has different semantics.
It is unnecessary for this raw-margin experimental checkpoint. Approximate contributions
are deliberately disabled. No claim of independent validation against a second SHAP
implementation is made; tests check native outputs and algebraic consistency.

## Exact contract

explanation-v1-experimental binds the full behavior-v1 vector (names, order, values), exact
model version, 29 contributions, base value, raw margin, uncalibrated score, method and
reference semantics. Technical contributions remain in feature order; none are dropped.
Native shapes must be (1,1,30) for contributions and (1,1) for margin/score. Unsupported
booster types, features, shapes, non-finite values and failed reconstruction are errors.

For binary:logistic, output_space=raw_margin_log_odds. Check:

- base_value + sum(all contributions) agrees with raw_margin using absolute tolerance
  1e-5 and relative tolerance 1e-6 (math.isclose semantics).
- Stable sigmoid(raw_margin) agrees with the native uncalibrated score within absolute
  tolerance 1e-6, with no relative tolerance.
- Explanation vector/model identity exactly match the risk result; its score agrees with
  the recorded prediction within absolute tolerance 1e-6.

Tolerances are fixed versioned numerical limits recorded in each technical explanation,
not fitted thresholds. A feature contribution is not a probability change. Do not apply
sigmoid separately to contributions, multiply log-odds contributions by hybrid weights,
or claim they sum to the rules/hybrid score. Base value is a model reference term, not a
customer baseline, population fraud rate or calibrated prior. Correlated features and
training weights affect attribution; values do not establish causality or legitimacy.

## Readable presentation and missingness

The full technical vector is accompanied by five contributions ranked by absolute magnitude;
original feature order breaks ties. Readable messages state the encoded feature value and
signed attribution to the model margin. Labels refer to bounded admitted/captured history,
including observed recipient activity age rather than recipient account age.

Availability masks explicitly mark imputed/unavailable values as placeholders. For example,
no activity means days_since_last_transfer=0 is not evidence of a recent transfer. A model
may attribute strongly to this placeholder; disclose it rather than suppressing its
contribution or inventing an observed fact. Missingness indicators are themselves actual
encoded inputs. Zero MAD and the denominator floor remain visible, not treated as missing
when sufficient baseline observations exist. All features still follow ADR-010 semantics.

Rules remain a separate set of evidence/reasons. Rules-only returns no model explanation
and imports no ML runtime. Hybrid may have INSUFFICIENT_EVIDENCE with a null final score
while still explaining the available model component. This does not remove its abstention.
No explanation error falls back to a fabricated explanation or emits a successful report.

## Integration, replay and boundaries

Add --explain to the existing offline risk CLI; existing callers retain their old output
unless opting in. All strategy/policy options and trusted manifest checks remain intact.
The report retains outer context fingerprint, model manifest pin, actual capture/inference/
evaluation clocks and full rule/risk policy. Explanation fields and readable order replay;
the existing actual inference/evaluation clocks change each invocation.

Runtime is CPU native TreeSHAP with the reviewed gbtree and full model iteration range.
The reference uses stored tree cover statistics; it is not an analyst-selected causal or
representative production baseline. No labels, new history or recaptured profiles enter
explanation. Current KZT/UTC/profile-window restrictions and synthetic-only eligibility
continue through the existing risk/inference service. Low-level vector APIs require callers
to honor that scope; the CLI always goes through the scoped service.

No HTTP route, database write, profile admission, model registration, case or operational
action is added. Legacy trained_at stays unknown. The atomic evaluation/context/assessment
and nullable provenance design in ADR-015 must precede future durable case orchestration.
All outputs remain experimental, uncalibrated, non-causal and production-ineligible.

## Verification

All 2,400 hash-verified original seed17 prepared rows passed native additivity and link checks:
maximum absolute margin reconstruction difference 2.2863969206809998e-6 and maximum sigmoid
score difference 8.22891939034065e-8. These are numerical implementation checks, not predictive
performance measurements. No benchmark/test labels were read for tuning or new evaluation.
Committed summary: ml/experiments/phase10-explanations/verification.json.
Actual saved-context hybrid CLI with --explain passed and retained insufficient evidence.

Tests cover native model parity, complete feature ordering, cold starts, missing placeholders,
zero MAD, signed ranking/ties, additivity/link limits, overflow, incompatible model/vector/
score, unsupported shapes/booster, native errors and rules-only/ML-only/hybrid CLI behavior.
Existing corruption/scope tests still apply through the unchanged trusted loader and risk path.
