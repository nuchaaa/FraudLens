"""Native-only experimental XGBoost adapter implementing the FraudModel port."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import numpy as np
from xgboost import Booster, DMatrix

from backend.adapters.ml.bundle import (
    MAX_METADATA_BYTES,
    MAX_MODEL_BYTES,
    ArtifactError,
    ExperimentalManifest,
    checked_bytes,
)
from backend.app.features.contracts import FeatureVector
from backend.app.fraud.ports import FraudPrediction


class ExperimentalXGBoostModel:
    def __init__(
        self,
        bundle: Path,
        *,
        expected_manifest_sha256: str,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        raw = checked_bytes(bundle / "manifest.json", expected_manifest_sha256, MAX_METADATA_BYTES)
        self.manifest = ExperimentalManifest.model_validate_json(raw)
        if version("xgboost") != self.manifest.xgboost_version:
            raise ArtifactError("unsupported XGBoost runtime version")
        report = json.loads(
            checked_bytes(
                bundle / "training-report.json",
                self.manifest.training_report_sha256,
                MAX_METADATA_BYTES,
            )
        )
        if not isinstance(report, dict) or not all(
            isinstance(report.get(key), dict) for key in ("artifacts", "packages")
        ):
            raise ArtifactError("invalid training report structure")
        if (
            report.get("status") != "complete"
            or report.get("experiment_version") != "synthetic-comparison-v1"
            or report.get("generator_version") != "synthetic-behavior-v1"
            or report.get("feature_version") != self.manifest.feature_version
            or tuple(report.get("feature_names", ())) != self.manifest.feature_names
            or report.get("source_sha256") != self.manifest.training_dataset_sha256
            or report.get("lock_sha256") != self.manifest.training_lock_sha256
            or report.get("seed") != self.manifest.seed
            or report.get("selected_model") != "xgboost"
            or report.get("synthetic_only") is not True
            or report.get("production_eligible") is not False
            or report.get("artifacts", {}).get("selected.joblib")
            != self.manifest.original_pickle_sha256
            or report.get("packages", {}).get("xgboost") != self.manifest.xgboost_version
        ):
            raise ArtifactError("manifest and training provenance disagree")
        raw_model = checked_bytes(bundle / "model.ubj", self.manifest.model_sha256, MAX_MODEL_BYTES)
        self._booster = Booster(params={"nthread": 1})
        self._booster.load_model(bytearray(raw_model))
        config = json.loads(self._booster.save_config())
        if (
            self._booster.num_features() != len(self.manifest.feature_names)
            or config["learner"]["objective"]["name"] != "binary:logistic"
        ):
            raise ArtifactError("unsupported model shape or objective")
        self._clock = clock

    def predict(self, features: FeatureVector) -> FraudPrediction:
        if (
            features.version != self.manifest.feature_version
            or features.names != self.manifest.feature_names
        ):
            raise ArtifactError("model requires exact feature version and order")
        values = np.asarray([features.values], dtype=np.float64)
        scores = self._booster.predict(DMatrix(values), validate_features=True)
        if scores.shape != (1,):
            raise ArtifactError("model must return one binary score")
        return FraudPrediction(
            float(scores[0]), self.manifest.model_version, features.version, self._clock()
        )
