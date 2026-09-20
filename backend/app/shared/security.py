from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Role(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    SERVICE = "service"


@dataclass(frozen=True)
class Principal:
    principal_id: UUID
    roles: frozenset[Role]
    customer_ids: frozenset[UUID] = frozenset()

    def can_read(self, customer_id: UUID) -> bool:
        return Role.ADMIN in self.roles or (
            bool(self.roles & {Role.ANALYST, Role.SERVICE}) and customer_id in self.customer_ids
        )

    def can_submit(self, customer_id: UUID) -> bool:
        return Role.ADMIN in self.roles or (
            Role.SERVICE in self.roles and customer_id in self.customer_ids
        )


class Forbidden(ValueError):
    """The authenticated principal cannot perform this operation."""


class NotFound(ValueError):
    """The requested resource does not exist or is outside the caller's scope."""
