"""Strict experimental bundle metadata; trust comes from an independently pinned digest."""

import hashlib
import hmac
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.features.engine import FEATURE_NAMES

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
MAX_METADATA_BYTES = 128 * 1024
MAX_MODEL_BYTES = 32 * 1024 * 1024


class ArtifactError(ValueError):
    pass


class ExperimentalManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    schema_version: Literal[1] = 1
    format: Literal["xgboost-ubj"] = "xgboost-ubj"
    model_version: str
    model_sha256: Digest
    feature_version: Literal["behavior-v1"] = "behavior-v1"
    feature_names: tuple[str, ...]
    training_report_sha256: Digest
    training_dataset_sha256: Digest
    training_lock_sha256: Digest
    original_pickle_sha256: Digest
    xgboost_version: str
    seed: Literal[17, 29, 43]
    exported_at: datetime
    trained_at: None = None
    status: Literal["CANDIDATE"] = "CANDIDATE"
    synthetic_only: Literal[True] = True
    production_eligible: Literal[False] = False
    calibrated: Literal[False] = False
    currency: Literal["KZT"] = "KZT"
    profile_timezone: Literal["UTC"] = "UTC"
    long_window_days: Literal[180] = 180
    short_window_days: Literal[30] = 30

    @model_validator(mode="after")
    def check_contract(self) -> "ExperimentalManifest":
        if self.feature_names != FEATURE_NAMES:
            raise ValueError("unsupported feature order")
        if self.model_version != f"experimental-xgb-{self.model_sha256}":
            raise ValueError("model version must identify exact native model bytes")
        if self.exported_at.tzinfo is None or self.exported_at.utcoffset() is None:
            raise ValueError("export time must be aware")
        return self


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_bounded(path: Path, limit: int) -> bytes:
    with path.open("rb") as source:
        result = source.read(limit + 1)
    if len(result) > limit:
        raise ArtifactError("artifact exceeds size limit")
    return result


def checked_bytes(path: Path, expected: str, limit: int) -> bytes:
    result = read_bounded(path, limit)
    if not hmac.compare_digest(sha256(result), expected):
        raise ArtifactError("artifact digest mismatch")
    return result
