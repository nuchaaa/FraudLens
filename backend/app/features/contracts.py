import math
from dataclasses import dataclass

from backend.app.shared.validation import nonempty


@dataclass(frozen=True)
class FeatureVector:
    """Ordered, immutable input shared by future training and online inference."""

    version: str
    names: tuple[str, ...]
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        nonempty(self.version, "feature version")
        if not self.names or len(self.names) != len(self.values):
            raise ValueError("features must be nonempty with matching names and values")
        if len(set(self.names)) != len(self.names):
            raise ValueError("feature names must be unique")
        for name in self.names:
            nonempty(name, "feature name")
        if any(not math.isfinite(value) for value in self.values):
            raise ValueError("features must be finite")
