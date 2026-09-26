"""Replay sequence-v1 evidence from a retained context without database access."""

import argparse
import json
import sys
from pathlib import Path

from backend.adapters.features.artifacts import read_context
from backend.app.sequence.engine import report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay experimental temporal fraud signals; no score or verdict"
    )
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(report(read_context(args.artifact)), default=str, allow_nan=False))
        return 0
    except (ValueError, OSError):
        print("Sequence replay failed: invalid artifact or path.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
