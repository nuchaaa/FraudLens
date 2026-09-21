# Offline ML

Run `python -m ml.src.training.experiment --output work/run --seed 17` from the repository
with the optional ml dependency group installed. The shared production extractor supplies
behavior-v1 inputs. No ML library enters backend/app. See development.md and ADR-012.

The original runner supports synthetic data. A separate `ml.src.training.ulb_benchmark`
runner uses hash-pinned external ULB v3 data with an incompatible ulb-pca-v1 contract.
Reports and local trained artifacts exist; all have production_eligible=false; only the original generator reports synthetic_only=true.
Retrospective external benchmark results now exist; production behavioral selection and
adaptive-profile research remain unfinished. See ADR-013 and the ULB source notice.
