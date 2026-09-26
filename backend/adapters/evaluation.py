"""Composition/serialization boundary for trusted experimental evaluation, no supplied scores."""

import json
from pathlib import Path

from pydantic import TypeAdapter

from backend.adapters.features.artifacts import ContextArtifact, encode_context
from backend.app.evaluation.contracts import EvaluationUnavailable
from backend.app.explainability.contracts import ExplainableFraudModel
from backend.app.explainability.service import RiskExplanation, explain_risk
from backend.app.features.context import FeatureContext
from backend.app.risk.service import ExperimentalRiskResult, RiskPolicy, Strategy, evaluate_risk
from backend.app.sequence.engine import SequenceResult, evaluate_sequence


class ExperimentalEvaluationEngine:
    def __init__(self, bundle: Path | None = None, manifest_sha256: str | None = None) -> None:
        self.model: ExplainableFraudModel | None = None
        self.manifest_json: str | None = None
        self.manifest_sha256 = manifest_sha256
        if (bundle is None) != (manifest_sha256 is None):
            raise ValueError("configure both experimental bundle and independent manifest digest")
        if bundle is not None and manifest_sha256 is not None:
            from backend.adapters.ml.bundle import MAX_METADATA_BYTES, checked_bytes
            from backend.adapters.ml.xgboost_model import ExperimentalXGBoostModel

            model = ExperimentalXGBoostModel(bundle, expected_manifest_sha256=manifest_sha256)
            self.model = model
            self.manifest_json = checked_bytes(
                bundle / "manifest.json", manifest_sha256, MAX_METADATA_BYTES
            ).decode()

    def render(
        self, context: FeatureContext, strategy: Strategy, manifest_sha256: str | None
    ) -> str:
        if strategy == Strategy.RULES_ONLY:
            if manifest_sha256 is not None:
                raise ValueError("rules-only cannot name a model")
        elif self.model is None or manifest_sha256 != self.manifest_sha256:
            raise EvaluationUnavailable("requested experimental model is not configured")
        try:
            result = evaluate_risk(context, RiskPolicy(strategy), model=self.model)
            explanation = explain_risk(result, model=self.model)
        except Exception as exc:
            # Native-library failures must roll back the complete use case; never fallback.
            if type(exc).__module__.startswith("xgboost"):
                raise EvaluationUnavailable("experimental model failed") from None
            raise
        risk = json.loads(TypeAdapter(ExperimentalRiskResult).dump_json(result))
        sequence = json.loads(TypeAdapter(SequenceResult).dump_json(evaluate_sequence(context)))
        if risk["prediction"] is not None:
            risk["prediction"]["uncalibrated_score"] = risk["prediction"].pop("probability")
        artifact = ContextArtifact.model_validate_json(encode_context(context))
        return json.dumps(
            {
                "context_artifact": artifact.model_dump(),
                "context_sha256": artifact.sha256,
                "risk": risk,
                # Supplemental evidence is retained but deliberately excluded from
                # risk-v1 scoring until a separately versioned policy is evaluated.
                "sequence_evidence": sequence,
                "explanation": json.loads(TypeAdapter(RiskExplanation).dump_json(explanation)),
                "model_manifest_json": self.manifest_json
                if strategy != Strategy.RULES_ONLY
                else None,
                "model_manifest_sha256": manifest_sha256,
                "production_eligible": False,
                "operational_action_executed": False,
                "admission_workflow_verified": False,
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
