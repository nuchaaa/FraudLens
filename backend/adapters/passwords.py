"""Explicit Argon2id policy for human passwords, never random API tokens."""

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

from backend.app.identity.policy import validate_password


class Argon2Passwords:
    def __init__(self) -> None:
        self._hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )

    def hash(self, password: str) -> str:
        validate_password(password)
        return self._hasher.hash(password)

    def verify(self, encoded: str, password: str) -> bool:
        try:
            validate_password(password)
        except ValueError:
            return False
        # Encoded hashes must come only from trusted account persistence. Never
        # accept caller-supplied Argon2 parameters or serialized password hashes.
        try:
            return self._hasher.verify(encoded, password)
        except (VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, encoded: str) -> bool:
        try:
            return self._hasher.check_needs_rehash(encoded)
        except InvalidHashError:
            return True
