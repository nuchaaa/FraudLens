"""Typed, framework-free explanation of one model output, never a causal verdict."""

import math
from dataclasses import dataclass, field
from typing import Protocol

from backend.app.features.contracts import FeatureVector
from backend.app.features.engine import FEATURE_NAMES
from backend.app.fraud.ports import FraudModel
from backend.app.shared.validation import nonempty, probability

MARGIN_ATOL = 1e-5
MARGIN_RTOL = 1e-6
SCORE_ATOL = 1e-6


def sigmoid(margin: float) -> float:
    if margin >= 0:
        return 1 / (1 + math.exp(-margin))
    exp = math.exp(margin)
    return exp / (1 + exp)


@dataclass(frozen=True)
class ModelExplanation:
    model_version: str
    features: FeatureVector
    contributions: tuple[float, ...]
    base_value: float
    raw_margin: float
    uncalibrated_score: float
    version: str = field(default="explanation-v1-experimental", init=False)
    method: str = field(default="xgboost-native-treeshap", init=False)
    output_space: str = field(default="raw_margin_log_odds", init=False)
    reference: str = field(default="model_internal_path_cover", init=False)
    margin_absolute_tolerance: float = field(default=MARGIN_ATOL, init=False)
    margin_relative_tolerance: float = field(default=MARGIN_RTOL, init=False)
    score_absolute_tolerance: float = field(default=SCORE_ATOL, init=False)

    def __post_init__(self) -> None:
        nonempty(self.model_version, "model version")
        if self.features.version != "behavior-v1" or self.features.names != FEATURE_NAMES:
            raise ValueError("explanation requires exact behavior-v1 feature order")
        if not isinstance(self.contributions, tuple) or len(self.contributions) != len(
            FEATURE_NAMES
        ):
            raise ValueError("explanation must contain all feature contributions")
        if not all(
            math.isfinite(v) for v in (*self.contributions, self.base_value, self.raw_margin)
        ):
            raise ValueError("explanation values must be finite")
        probability(self.uncalibrated_score)
        try:
            reconstructed = math.fsum((self.base_value, *self.contributions))
        except OverflowError:
            raise ValueError("explanation sum overflow") from None
        if not math.isclose(
            reconstructed,
            self.raw_margin,
            abs_tol=MARGIN_ATOL,
            rel_tol=MARGIN_RTOL,
        ):
            raise ValueError("explanation contributions do not reconstruct model margin")
        if not math.isclose(
            sigmoid(self.raw_margin), self.uncalibrated_score, abs_tol=SCORE_ATOL, rel_tol=0
        ):
            raise ValueError("explanation margin does not reconstruct model score")


class ExplainableFraudModel(FraudModel, Protocol):
    def explain(self, features: FeatureVector) -> ModelExplanation: ...
