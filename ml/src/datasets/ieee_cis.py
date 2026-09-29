"""Pinned IEEE-CIS training CSV reader for a separate retrospective benchmark."""

import csv
import math
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from ml.src.datasets.ulb import sha256

SOURCE_URL = "https://www.kaggle.com/competitions/ieee-fraud-detection/data"
SOURCE_HASHES = {
    "train_transaction.csv": "3a5c83ab6b3cc13dcabe5ffa9f522307fd5f7f7b6e6f6a60c32284ca6283d642",
    "train_identity.csv": "b63c725d8377be90a995268d97f347c17d456b95db45807adcf9f59cd603c37c",
}
MAX_TRANSACTION_BYTES = 750_000_000
MAX_IDENTITY_BYTES = 50_000_000
MISSING = "__MISSING__"
CATEGORICAL_FIELDS = ("product", "card4", "card6", "device_type")
SOURCE_COLUMNS = (
    "TransactionID",
    "TransactionDT",
    "TransactionAmt",
    "isFraud",
    "ProductCD",
    "card4",
    "card6",
)


@dataclass(frozen=True, slots=True)
class CisRow:
    transaction_id: int
    time: int
    amount: float
    label: int
    product: str
    card4: str
    card6: str
    device_type: str


@dataclass(frozen=True, slots=True)
class CisData:
    rows: tuple[CisRow, ...]
    identity_rows: int
    matched_identity_rows: int


def _header(reader: Iterator[list[str]], required: tuple[str, ...]) -> tuple[dict[str, int], int]:
    header = next(reader, None)
    if header is None or len(header) != len(set(header)):
        raise ValueError("unsupported IEEE-CIS CSV header")
    if any(name not in header for name in required):
        raise ValueError("unsupported IEEE-CIS CSV header")
    return {name: header.index(name) for name in required}, len(header)


def _natural(raw: str, field: str) -> int:
    if not raw.isdecimal():
        raise ValueError(f"{field} must be a nonnegative integer")
    return int(raw)


def _category(raw: str) -> str:
    return sys.intern(raw if raw else MISSING)


def read_csv(transaction_path: Path, identity_path: Path) -> CisData:
    """Parse selected fields; no labels or rows are written or repaired."""
    if transaction_path.stat().st_size > MAX_TRANSACTION_BYTES:
        raise ValueError("transaction source exceeds size limit")
    if identity_path.stat().st_size > MAX_IDENTITY_BYTES:
        raise ValueError("identity source exceeds size limit")
    identities: dict[int, str] = {}
    with identity_path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.reader(source)
        positions, width = _header(reader, ("TransactionID", "DeviceType"))
        for fields in reader:
            if len(fields) != width:
                raise ValueError("identity row has incorrect width")
            identifier = _natural(fields[positions["TransactionID"]], "TransactionID")
            if identifier in identities:
                raise ValueError("duplicate identity TransactionID")
            identities[identifier] = _category(fields[positions["DeviceType"]])
    identity_count = len(identities)
    rows: list[CisRow] = []
    seen: set[int] = set()
    matched = 0
    with transaction_path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.reader(source)
        positions, width = _header(reader, SOURCE_COLUMNS)
        for fields in reader:
            if len(fields) != width:
                raise ValueError("transaction row has incorrect width")
            identifier = _natural(fields[positions["TransactionID"]], "TransactionID")
            if identifier in seen:
                raise ValueError("duplicate transaction TransactionID")
            seen.add(identifier)
            time = _natural(fields[positions["TransactionDT"]], "TransactionDT")
            try:
                amount = float(fields[positions["TransactionAmt"]])
            except ValueError as error:
                raise ValueError("TransactionAmt must be finite and positive") from error
            if not math.isfinite(amount) or amount <= 0:
                raise ValueError("TransactionAmt must be finite and positive")
            label_raw = fields[positions["isFraud"]]
            if label_raw not in ("0", "1"):
                raise ValueError("isFraud must be binary")
            if identifier in identities:
                matched += 1
            rows.append(
                CisRow(
                    identifier,
                    time,
                    amount,
                    int(label_raw),
                    _category(fields[positions["ProductCD"]]),
                    _category(fields[positions["card4"]]),
                    _category(fields[positions["card6"]]),
                    identities.get(identifier, MISSING),
                )
            )
    if not rows:
        raise ValueError("benchmark source must not be empty")
    if set(identities) - seen:
        raise ValueError("identity row has no matching transaction")
    rows.sort(key=lambda row: (row.time, row.transaction_id))
    return CisData(tuple(rows), identity_count, matched)


def load_pinned(folder: Path) -> CisData:
    for name, expected in SOURCE_HASHES.items():
        if sha256(folder / name) != expected:
            raise ValueError(f"{name} content hash differs from pinned source")
    return read_csv(folder / "train_transaction.csv", folder / "train_identity.csv")


def split_rows(data: CisData) -> tuple[dict[str, tuple[CisRow, ...]], int, int]:
    """Choose split boundaries from relative offsets only, never labels."""
    rows = data.rows
    if len(rows) < 10:
        raise ValueError("too few rows for frozen three-way split")
    train_end = rows[int(0.60 * len(rows))].time
    validation_end = rows[int(0.80 * len(rows))].time
    if train_end >= validation_end:
        raise ValueError("time quantile boundaries collapsed")
    parts = {
        "train": tuple(row for row in rows if row.time < train_end),
        "validation": tuple(row for row in rows if train_end <= row.time < validation_end),
        "test": tuple(row for row in rows if row.time >= validation_end),
    }
    for name, part in parts.items():
        if {row.label for row in part} != {0, 1}:
            raise ValueError(f"{name} requires both classes; boundaries must not change")
    return parts, train_end, validation_end
