"""Trusted local operator CLI; passwords are read from a terminal, never argv."""

import argparse
import getpass
from functools import partial
from uuid import UUID

from backend.adapters.database.base import create_database_engine
from backend.adapters.database.uow import create_unit_of_work
from backend.adapters.passwords import Argon2Passwords
from backend.adapters.security import CredentialRegistry
from backend.app.identity.service import IdentityService
from backend.app.shared.security import Role
from backend.config import Settings


def _password() -> str:
    first = getpass.getpass("Password: ")
    again = getpass.getpass("Repeat password: ")
    if first != again:
        raise ValueError("password entries differ")
    return first


def main() -> None:
    parser = argparse.ArgumentParser(description="Audited local human-account operations")
    parser.add_argument(
        "action", choices=("provision", "recover", "disable", "enable", "set-policy")
    )
    parser.add_argument("--operator-id", type=UUID, required=True)
    parser.add_argument("--account-id", type=UUID)
    parser.add_argument("--login")
    parser.add_argument("--role", choices=("analyst", "admin"))
    parser.add_argument("--customer-id", type=UUID, action="append")
    args = parser.parse_args()
    settings = Settings()
    if settings.database_url is None:
        parser.error("FRAUDLENS_DATABASE_URL is required")
    registry = CredentialRegistry(
        settings.api_principals.get_secret_value() if settings.api_principals else None
    )
    engine = create_database_engine(settings.database_url.get_secret_value())
    try:
        service = IdentityService(
            partial(create_unit_of_work, engine),
            Argon2Passwords(),
            service_principal_ids=registry.principal_ids,
        )
        service.ensure_no_collisions()
        if args.action == "provision":
            if args.account_id or not args.login or not args.role:
                parser.error("provision requires --login and --role, without --account-id")
            account_id = service.provision(
                args.login,
                _password(),
                Role(args.role),
                frozenset(args.customer_id or ()),
                operator_id=args.operator_id,
            )
            print(f"Provisioned human account {account_id}")
        else:
            if not args.account_id or args.login:
                parser.error("operation requires --account-id and no --login")
            if args.action == "recover":
                service.change(args.account_id, operator_id=args.operator_id, password=_password())
            elif args.action == "disable":
                service.change(args.account_id, operator_id=args.operator_id, active=False)
            elif args.action == "enable":
                service.change(args.account_id, operator_id=args.operator_id, active=True)
            else:
                if not args.role:
                    parser.error("set-policy requires --role")
                service.change(
                    args.account_id,
                    operator_id=args.operator_id,
                    role=Role(args.role),
                    customer_ids=frozenset(args.customer_id or ()),
                )
            print(f"Updated human account {args.account_id}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
