# ADR-004: Compare models before choosing a baseline

Status: accepted for the foundation; unimplemented parts explicitly noted.

## Context

Tree ensembles may capture behavioral interactions, but presumed superiority is not evidence.

## Decision

Compare Logistic Regression, Random Forest and XGBoost offline. XGBoost is a candidate, not the selected production model.

## Alternatives

Select XGBoost immediately; train on every analyst decision.

## Why alternatives were rejected

Premature selection risks complexity without benefit; online retraining leaks noisy labels and harms reproducibility.

## Consequences

No trained model or predictive metrics exist at this checkpoint. Lock ML dependencies in Phase 7. Select using validation PR-AUC plus operating-point recall/FPR constraints, then evaluate once on held-out time periods.
