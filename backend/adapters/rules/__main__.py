"""Evaluate saved synthetic feature contexts without database access."""

import argparse
import json
import sys
from pathlib import Path

from backend.adapters.features.artifacts import read_context
from backend.app.rules.engine import RulePolicy, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay experimental fraud rules; no risk verdict")
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--amount-median-ratio", type=float, default=10.0)
    parser.add_argument("--prior-transfers-5-min", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        policy = RulePolicy(args.amount_median_ratio, args.prior_transfers_5_min)
        result = report(read_context(args.artifact), policy)
        print(json.dumps(result, allow_nan=False))
        return 0
    except (ValueError, OSError):
        print("Rule replay failed: invalid policy, artifact or path.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
