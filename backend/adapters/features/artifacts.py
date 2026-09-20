"""Versioned portable inputs for exact feature replay; digests are not signatures."""

import hashlib
import hmac
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from backend.app.features.context import FeatureContext, FeatureInputError

MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
_context_adapter = TypeAdapter(FeatureContext)


class ContextArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1] = 1
    feature_version: Literal["behavior-v1"] = "behavior-v1"
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload: str


def encode_context(context: FeatureContext) -> str:
    payload = _context_adapter.dump_json(context, warnings="error").decode("utf-8")
    # Validate our own serialized contract before emitting a reusable artifact.
    _context_adapter.validate_json(payload, strict=True, extra="forbid")
    result = ContextArtifact(
        sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        payload=payload,
    ).model_dump_json()
    if len(result.encode("utf-8")) > MAX_ARTIFACT_BYTES:
        raise FeatureInputError("feature context artifact exceeds 16 MiB")
    return result


def decode_context(document: str) -> FeatureContext:
    if len(document.encode("utf-8")) > MAX_ARTIFACT_BYTES:
        raise FeatureInputError("feature context artifact exceeds 16 MiB")
    try:
        artifact = ContextArtifact.model_validate_json(document)
        actual = hashlib.sha256(artifact.payload.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(actual, artifact.sha256):
            raise FeatureInputError("feature context digest mismatch")
        return _context_adapter.validate_json(artifact.payload, strict=True, extra="forbid")
    except (ValidationError, KeyError, OverflowError):
        # Do not echo possibly sensitive raw history from a malformed artifact.
        raise FeatureInputError("invalid feature context artifact") from None


def write_context(path: Path, context: FeatureContext) -> None:
    """Explicit caller-owned export; never overwrite a captured input artifact."""
    document = encode_context(context)
    with path.open("x", encoding="utf-8") as output:
        output.write(document)


def read_context(path: Path) -> FeatureContext:
    with path.open("rb") as source:
        document = source.read(MAX_ARTIFACT_BYTES + 1)
    if len(document) > MAX_ARTIFACT_BYTES:
        raise FeatureInputError("feature context artifact exceeds 16 MiB")
    try:
        return decode_context(document.decode("utf-8"))
    except UnicodeDecodeError:
        raise FeatureInputError("feature context artifact must be UTF-8") from None
