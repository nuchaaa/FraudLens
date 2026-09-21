"""Replay risk policies locally; no database access or operational actions."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import TypeAdapter

from backend.adapters.features.artifacts import ContextArtifact, encode_context, read_context
from backend.app.decision.policy import DecisionPolicy
from backend.app.risk.service import ExperimentalRiskResult, RiskPolicy, Strategy, evaluate_risk
from backend.app.rules.engine import RulePolicy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experimental read-only Risk + Decision replay")
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--strategy", choices=list(Strategy), required=True)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--model-weight", type=float, default=0.5)
    parser.add_argument("--rule-weights", type=float, nargs=5, default=(0.4, 0.15, 0.25, 0.1, 0.1))
    parser.add_argument("--amount-median-ratio", type=float, default=10)
    parser.add_argument("--prior-transfers-5-min", type=int, default=5)
    parser.add_argument("--medium", type=float, default=0.35)
    parser.add_argument("--high", type=float, default=0.65)
    parser.add_argument("--critical", type=float, default=0.85)
    args = parser.parse_args(argv)
    errors: tuple[type[Exception], ...] = (ValueError, OSError, KeyError, TypeError, ImportError)
    try:
        policy = RiskPolicy(
            Strategy(args.strategy),
            args.model_weight,
            tuple(args.rule_weights),
            RulePolicy(args.amount_median_ratio, args.prior_transfers_5_min),
            DecisionPolicy(args.medium, args.high, args.critical),
        )
        context = read_context(args.context)
        model = None
        if policy.strategy == Strategy.RULES_ONLY:
            if args.bundle is not None or args.manifest_sha256 is not None:
                raise ValueError("rules-only does not accept model settings")
        else:
            if args.bundle is None or args.manifest_sha256 is None:
                raise ValueError("model strategies require bundle and trusted manifest digest")
            from xgboost.core import XGBoostError

            from backend.adapters.ml.xgboost_model import ExperimentalXGBoostModel

            errors = (*errors, XGBoostError)
            model = ExperimentalXGBoostModel(
                args.bundle, expected_manifest_sha256=args.manifest_sha256
            )
        result = evaluate_risk(context, policy, model=model)
        document = json.loads(TypeAdapter(ExperimentalRiskResult).dump_json(result))
        # Preserve internal port compatibility without claiming calibrated probability.
        if document["prediction"] is not None:
            document["prediction"]["uncalibrated_score"] = document["prediction"].pop("probability")
        document["context_sha256"] = ContextArtifact.model_validate_json(
            encode_context(context)
        ).sha256
        document["manifest_sha256"] = args.manifest_sha256
        document["synthetic_model_only"] = model is not None
        print(json.dumps(document, allow_nan=False))
        return 0
    except errors:
        print(
            "Experimental risk replay failed: invalid policy, input or model artifact.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
