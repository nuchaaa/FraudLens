from dataclasses import dataclass
from typing import Protocol

from backend.app.features.contracts import FeatureVector
from backend.app.risk.entities import RiskReason
from backend.app.shared.validation import nonempty


@dataclass(frozen=True)
class RuleVersion:
    version: str
    description: str

    def __post_init__(self) -> None:
        nonempty(self.version, "rule version")
        nonempty(self.description, "description")


class FraudSpecification(Protocol):
    def evaluate(self, features: FeatureVector) -> RiskReason | None: ...
