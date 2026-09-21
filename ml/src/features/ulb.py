"""Separate anonymized benchmark contract; never substitute for behavior-v1."""

from backend.app.features.contracts import FeatureVector

ULB_FEATURE_VERSION = "ulb-pca-v1"
ULB_FEATURE_NAMES = (*(f"V{i}" for i in range(1, 29)), "Amount")


def extract_ulb_features(values: tuple[float, ...]) -> FeatureVector:
    vector = FeatureVector(ULB_FEATURE_VERSION, ULB_FEATURE_NAMES, values)
    if vector.values[-1] < 0:
        raise ValueError("benchmark amount cannot be negative")
    return vector
