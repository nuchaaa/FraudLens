"""Authenticated local capture and offline replay; no model inference is performed."""

import argparse
import getpass
import json
import os
import sys
from functools import partial
from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from backend.adapters.database.base import create_database_engine
from backend.adapters.database.uow import create_unit_of_work
from backend.adapters.features.artifacts import read_context, write_context
from backend.adapters.security import CredentialRegistry
from backend.app.features.context import FeatureInputError
from backend.app.features.engine import extract_features
from backend.app.features.service import FeatureService
from backend.app.shared.security import NotFound
from backend.config import Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture/replay FraudLens feature inputs; no scoring"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser(
        "capture", help="authenticate and save input facts without overwriting"
    )
    capture.add_argument("--transaction-id", type=UUID, required=True)
    selection = capture.add_mutually_exclusive_group(required=True)
    selection.add_argument("--profile-version", type=int)
    selection.add_argument(
        "--without-profile",
        action="store_true",
        help="assert that no profile currently exists for this currency",
    )
    capture.add_argument("--output", type=Path, required=True)
    replay = commands.add_parser(
        "replay", help="extract features solely from a saved local context"
    )
    replay.add_argument("artifact", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            settings = Settings()
            registry = CredentialRegistry(
                settings.api_principals.get_secret_value() if settings.api_principals else None,
            )
            token = os.environ.get("FRAUDLENS_FEATURE_TOKEN") or getpass.getpass("Bearer token: ")
            principal = registry.authenticate(token)
            if principal is None:
                raise FeatureInputError("valid bearer credential required")
            if settings.database_url is None:
                raise FeatureInputError("database is not configured")
            engine = create_database_engine(settings.database_url.get_secret_value())
            try:
                context = FeatureService(partial(create_unit_of_work, engine)).capture(
                    principal,
                    args.transaction_id,
                    profile_version=args.profile_version,
                )
                vector = extract_features(context)
                write_context(args.output, context)
            finally:
                engine.dispose()
        else:
            context = read_context(args.artifact)
            vector = extract_features(context)
        print(
            json.dumps(
                {
                    "context_id": str(context.context_id),
                    "feature_version": vector.version,
                    "profile_version": context.profile.version
                    if context.profile is not None
                    else None,
                    "admission_workflow_verified": False,
                    "features": dict(zip(vector.names, vector.values, strict=True)),
                },
                allow_nan=False,
            )
        )
        return 0
    except (FeatureInputError, NotFound) as exc:
        print(str(exc), file=sys.stderr)
    except (SQLAlchemyError, OSError, ValueError):
        print(
            "Feature operation failed: check storage, configuration or artifact path.",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
