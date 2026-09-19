# ADR-006: Safe profile update gate

Status: accepted for the foundation; unimplemented parts explicitly noted.

## Context

An exceptional legitimate purchase must not normalize subsequent anomalous activity.

## Decision

Use rolling robust statistics and a separate update gate. Reject confirmed fraud, quarantine unverified or exceptional amounts, admit ordinary confirmed activity. Keep currency-specific profiles.

## Alternatives

Learn from all received transactions; rely only on arithmetic mean; block all adaptation.

## Why alternatives were rejected

Blind learning enables poisoning, the mean is outlier-sensitive, and no adaptation prevents legitimate drift.

## Consequences

The initial 10× median and minimum five trusted observations are configurable uncalibrated assumptions. Cold start fails closed; trusted enrollment is future work. Low-weight updates are reserved, not applied. The gate cannot protect against compromised analyst labels. Retraction of previously admitted fraud requires event-history replay, not an inverse mean update.
