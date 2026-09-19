from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from backend.app.features.contracts import FeatureVector
from backend.app.shared.validation import nonempty, probability, utc


@dataclass(frozen=True)
class FraudPrediction:
    probability: float
    model_version: str
    feature_version: str
    timestamp: datetime

    def __post_init__(self) -> None:
        probability(self.probability)
        nonempty(self.model_version, "model version")
        nonempty(self.feature_version, "feature version")
        object.__setattr__(self, "timestamp", utc(self.timestamp))


class FraudModel(Protocol):
    def predict(self, features: FeatureVector) -> FraudPrediction: ...


class ModelStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    PRODUCTION = "PRODUCTION"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class ModelVersion:
    version: str
    feature_version: str
    trained_at: datetime
    artifact_sha256: str
    status: ModelStatus = ModelStatus.CANDIDATE
    metrics: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        nonempty(self.version, "version")
        nonempty(self.feature_version, "feature_version")
        if len(self.artifact_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in self.artifact_sha256
        ):
            raise ValueError("artifact digest must be lowercase SHA-256")
        if len({name for name, _ in self.metrics}) != len(self.metrics):
            raise ValueError("duplicate model metric")
        for name, value in self.metrics:
            nonempty(name, "metric name")
            probability(value)
        object.__setattr__(self, "trained_at", utc(self.trained_at))
