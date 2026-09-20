"""Configured high-entropy service credentials; no passwords or user sessions."""

import hashlib
import hmac
import re
from datetime import UTC, datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from backend.app.shared.security import Principal, Role


class Credential(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    principal_id: UUID
    token_sha256: str = Field(pattern=r"^[0-9a-f]{64}$", repr=False)
    roles: frozenset[Role] = Field(min_length=1)
    customer_ids: frozenset[UUID] = frozenset()
    expires_at: AwareDatetime


class CredentialRegistry:
    def __init__(self, configuration: str | None) -> None:
        try:
            self._credentials = TypeAdapter(tuple[Credential, ...]).validate_json(
                configuration if configuration is not None else "[]"
            )
        except ValidationError:
            raise ValueError("invalid API principal configuration") from None
        if len({c.principal_id for c in self._credentials}) != len(self._credentials) or len(
            {c.token_sha256 for c in self._credentials}
        ) != len(self._credentials):
            raise ValueError("API principal IDs and token digests must be unique")

    def authenticate(self, token: str, *, now: datetime | None = None) -> Principal | None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            return None
        digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        current = now or datetime.now(UTC)
        match: Credential | None = None
        for credential in self._credentials:
            if hmac.compare_digest(digest, credential.token_sha256):
                match = credential
        if match is None or match.expires_at <= current:
            return None
        return Principal(match.principal_id, match.roles, match.customer_ids)
