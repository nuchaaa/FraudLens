"""Explicit local database-operator command; never started by the HTTP application."""

import argparse
import json
import os
from dataclasses import asdict

from sqlalchemy.exc import SQLAlchemyError

from backend.adapters.database.base import create_database_engine
from backend.adapters.database.delivery import PostgresDeliveryQueue, PostgresRecordingConsumer
from backend.adapters.database.grants import verify_runtime_role
from backend.app.shared.delivery import dispatch
from backend.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Local recording outbox worker (no external effects)"
    )
    parser.add_argument("command", choices=("run", "status"))
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("limit must be between 1 and 1000")
    url = os.environ.get("FRAUDLENS_DATABASE_URL")
    if not url:
        parser.error("FRAUDLENS_DATABASE_URL is required")
    engine = create_database_engine(url)
    try:
        if Settings().environment == "production":
            with engine.connect() as connection:
                verify_runtime_role(connection, "worker")
        queue = PostgresDeliveryQueue(engine)
        result = (
            asdict(dispatch(queue, PostgresRecordingConsumer(engine), limit=args.limit))
            if args.command == "run"
            else queue.status()
        )
        print(json.dumps(result, sort_keys=True))
    except SQLAlchemyError:
        parser.exit(1, "Outbox storage operation failed; inspect database availability.\n")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
