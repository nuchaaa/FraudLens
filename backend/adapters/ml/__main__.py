"""Offline native model replay; no database or operational decisions."""

import argparse
import json
import sys
from pathlib import Path

from xgboost.core import XGBoostError

from backend.adapters.features.artifacts import read_context
from backend.adapters.ml.xgboost_model import ExperimentalXGBoostModel
from backend.app.fraud.service import predict_experimental_context


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experimental synthetic model replay only")
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--context", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        model = ExperimentalXGBoostModel(args.bundle, expected_manifest_sha256=args.manifest_sha256)
        context = read_context(args.context)
        prediction = predict_experimental_context(model, context)
        print(
            json.dumps(
                {
                    "context_id": str(context.context_id),
                    "transaction_id": str(context.candidate.transaction_id),
                    "model_version": prediction.model_version,
                    "feature_version": prediction.feature_version,
                    "predicted_at": prediction.timestamp.isoformat(),
                    "uncalibrated_score": prediction.probability,
                    "synthetic_only": True,
                    "production_eligible": False,
                    "calibrated": False,
                    "admission_workflow_verified": False,
                    "manifest_sha256": args.manifest_sha256,
                },
                allow_nan=False,
            )
        )
        return 0
    except (ValueError, OSError, XGBoostError, KeyError, TypeError):
        print(
            "Experimental inference failed: incompatible input or untrusted artifact.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
