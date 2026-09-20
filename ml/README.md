# Offline ML

Run `python -m ml.src.training.experiment --output work/run --seed 17` from the repository
with the optional ml dependency group installed. The shared production extractor supplies
behavior-v1 inputs. No ML library enters backend/app. See development.md and ADR-012.

The current runner supports only original synthetic data, not arbitrary external datasets.
Reports and local trained artifacts exist; all are synthetic_only and production_eligible=false.
External validation, production selection and adaptive-profile research remain unfinished.
