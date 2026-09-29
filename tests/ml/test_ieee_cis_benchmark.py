"""Small fictional CSVs exercise the separate IEEE-CIS benchmark contract."""

import csv
import json
from pathlib import Path

import joblib
import pytest

from ml.src.datasets import ieee_cis
from ml.src.training import ieee_cis_benchmark

TRANSACTION_HEADER = (
    "TransactionID",
    "TransactionDT",
    "TransactionAmt",
    "isFraud",
    "ProductCD",
    "card4",
    "card6",
)
IDENTITY_HEADER = ("TransactionID", "DeviceType")


def write_csv(path: Path, header: tuple[str, ...], rows: list[tuple[object, ...]]) -> Path:
    with path.open("w", newline="") as source:
        writer = csv.writer(source)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def fixture_source(folder: Path, count: int = 20) -> tuple[Path, Path]:
    folder.mkdir()
    transactions = [
        (1000 + index, index, 100 + index, index % 2, "W", "visa", "debit")
        for index in range(count)
    ]
    identities = [(1000 + index, "desktop") for index in range(0, count, 2)]
    return (
        write_csv(folder / "train_transaction.csv", TRANSACTION_HEADER, transactions),
        write_csv(folder / "train_identity.csv", IDENTITY_HEADER, identities),
    )


def test_chronological_split_identity_join_and_train_only_categories(tmp_path: Path) -> None:
    transaction, identity = fixture_source(tmp_path / "source")
    data = ieee_cis.read_csv(transaction, identity)
    assert len(data.rows) == 20
    assert data.identity_rows == data.matched_identity_rows == 10
    assert data.rows[0].device_type == "desktop"
    assert data.rows[1].device_type == ieee_cis.MISSING
    parts, train_end, validation_end = ieee_cis.split_rows(data)
    assert (train_end, validation_end) == (12, 16)
    assert [len(part) for part in parts.values()] == [12, 4, 4]
    vocabulary = ieee_cis_benchmark.category_vocabulary(parts["train"])
    assert "unseen" not in vocabulary["product"]
    unseen = ieee_cis.CisRow(9999, 18, 7.0, 1, "unseen", "visa", "debit", "desktop")
    values, labels = ieee_cis_benchmark.arrays((unseen,), vocabulary)
    assert labels.tolist() == [1.0]
    assert values[0, 0] == 7.0
    assert values[0, list(vocabulary["product"].values())].sum() == 0


@pytest.mark.parametrize("problem", ["duplicate", "amount", "label", "time", "orphan", "width"])
def test_source_rejects_invalid_rows(tmp_path: Path, problem: str) -> None:
    transaction, identity = fixture_source(tmp_path / "source")
    with transaction.open(newline="") as source:
        transaction_rows = list(csv.reader(source))
    with identity.open(newline="") as source:
        identity_rows = list(csv.reader(source))
    if problem == "duplicate":
        transaction_rows.append(transaction_rows[1].copy())
    elif problem == "amount":
        transaction_rows[1][2] = "nan"
    elif problem == "label":
        transaction_rows[1][3] = "2"
    elif problem == "time":
        transaction_rows[1][1] = "-1"
    elif problem == "orphan":
        identity_rows.append(["999999", "mobile"])
    elif problem == "width":
        transaction_rows[1].append("unexpected")
    write_csv(transaction, TRANSACTION_HEADER, [tuple(row) for row in transaction_rows[1:]])
    write_csv(identity, IDENTITY_HEADER, [tuple(row) for row in identity_rows[1:]])
    with pytest.raises(ValueError):
        ieee_cis.read_csv(transaction, identity)


def test_pinned_bytes_and_missing_class_fail_closed(tmp_path: Path) -> None:
    transaction, identity = fixture_source(tmp_path / "source")
    with pytest.raises(ValueError, match="hash differs"):
        ieee_cis.load_pinned(transaction.parent)
    data = ieee_cis.read_csv(transaction, identity)
    all_zero = ieee_cis.CisData(
        tuple(
            ieee_cis.CisRow(
                row.transaction_id,
                row.time,
                row.amount,
                0,
                row.product,
                row.card4,
                row.card6,
                row.device_type,
            )
            for row in data.rows
        ),
        data.identity_rows,
        data.matched_identity_rows,
    )
    with pytest.raises(ValueError, match="both classes"):
        ieee_cis.split_rows(all_zero)


def test_runner_create_only_and_local_model_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transaction, identity = fixture_source(tmp_path / "source")
    data = ieee_cis.read_csv(transaction, identity)
    monkeypatch.setattr(ieee_cis_benchmark, "load_pinned", lambda source: data)
    output = tmp_path / "run"
    report = ieee_cis_benchmark.run(transaction.parent, output)
    assert report["production_eligible"] is False
    assert report["behavioral_compatible"] is False
    assert report["calibrated"] is False
    assert report["split_counts"]["test"] == {"rows": 4, "positives": 2}
    assert len(json.loads((output / "test_predictions.json").read_text())) == 4
    assert joblib.load(output / "selected.joblib") is not None
    with pytest.raises(FileExistsError):
        ieee_cis_benchmark.run(transaction.parent, output)
