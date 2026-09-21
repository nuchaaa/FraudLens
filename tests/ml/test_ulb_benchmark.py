import csv
import io
import json
import zipfile
from pathlib import Path

import joblib
import pytest

from backend.app.rules.engine import evaluate_rules
from ml.src.datasets import ulb
from ml.src.features.ulb import ULB_FEATURE_NAMES, ULB_FEATURE_VERSION, extract_ulb_features
from ml.src.training import ulb_benchmark
from ml.src.training.experiment import metrics


def write_csv(path: Path, rows: list[list[float]], header: tuple[str, ...] = ulb.HEADER) -> Path:
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def row(time: float, value: float, label: float) -> list[float]:
    return [time, value, *([0.0] * 27), 12.0, label]


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    return write_csv(
        tmp_path / "fixture.csv",
        [row(t, i, i % 2) for i, t in enumerate((0, 86399, 86400, 129599, 129600, 172000))],
    )


def test_contract_separate_from_behavioral_features() -> None:
    values = (-1.0, *([0.0] * 27), 0.0)
    vector = extract_ulb_features(values)
    assert vector.version == ULB_FEATURE_VERSION
    assert vector.names == ULB_FEATURE_NAMES
    assert vector.values == values
    assert "Time" not in vector.names and "Class" not in vector.names
    with pytest.raises(ValueError, match="behavior-v1"):
        evaluate_rules(vector)


def test_fixed_boundaries_and_immutable_arrays(csv_path: Path) -> None:
    data = ulb.read_csv(csv_path)
    masks = ulb.split_masks(data)
    assert data.source_rows.tolist() == [2, 3, 4, 5, 6, 7]
    assert [data.times[mask].tolist() for mask in masks.values()] == [
        [0, 86399],
        [86400, 129599],
        [129600, 172000],
    ]
    with pytest.raises(ValueError):
        data.features[0, 0] = 99


def test_duplicates_use_earliest_feature_occurrence_not_target(tmp_path: Path) -> None:
    source = write_csv(
        tmp_path / "source.csv", [row(129600, 5, 1), row(2, 5, 0), row(2, 5, 1), row(4, 6, 1)]
    )
    data = ulb.read_csv(source)
    assert data.raw_rows == 4 and data.excluded_duplicate_features == 2
    assert data.source_rows.tolist() == [3, 5]
    assert data.labels.tolist() == [0, 1]
    source = write_csv(source, [row(129600, 5, 0), row(2, 5, 1), row(2, 5, 0), row(4, 6, 0)])
    assert ulb.read_csv(source).source_rows.tolist() == [3, 5]


@pytest.mark.parametrize(
    "kind",
    ["header", "extra", "missing", "nan", "negative_time", "negative_amount", "class", "empty"],
)
def test_invalid_rows_rejected(tmp_path: Path, kind: str) -> None:
    values = row(0, 0, 0)
    header = ulb.HEADER
    if kind == "header":
        header = tuple(reversed(header))
    elif kind == "extra":
        values.append(0)
    elif kind == "missing":
        values.pop()
    elif kind == "nan":
        values[2] = float("nan")
    elif kind == "negative_time":
        values[0] = -1
    elif kind == "negative_amount":
        values[-2] = -1
    elif kind == "class":
        values[-1] = 2
    source = write_csv(tmp_path / "bad.csv", [] if kind == "empty" else [values], header)
    with pytest.raises(ValueError):
        ulb.read_csv(source)


def test_content_pin_and_single_class_fail(csv_path: Path) -> None:
    with pytest.raises(ValueError, match="hash"):
        ulb.load_pinned(csv_path)
    data = ulb.read_csv(csv_path)
    data.labels.flags.writeable = True
    data.labels[:] = 0
    with pytest.raises(ValueError, match="both classes"):
        ulb.split_masks(data)


def test_fetch_pin_and_create_only(
    csv_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as writer:
        writer.writestr("creditcard.csv", csv_path.read_bytes())
        writer.writestr("../unwanted", "never extract me")
    payload = archive.getvalue()
    monkeypatch.setattr(ulb.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(payload))
    monkeypatch.setattr(ulb, "CSV_SHA256", ulb.sha256(csv_path))
    output = tmp_path / "download"
    ulb.fetch(output)
    assert (output / "creditcard.csv").read_bytes() == csv_path.read_bytes()
    assert not (tmp_path / "unwanted").exists()
    assert json.loads((output / "source.json").read_text())["version"] == 3
    with pytest.raises(FileExistsError):
        ulb.fetch(output)
    monkeypatch.setattr(ulb, "CSV_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="differs"):
        ulb.fetch(tmp_path / "bad-hash")
    monkeypatch.setattr(ulb, "MAX_SOURCE_BYTES", 1)
    with pytest.raises(ValueError, match="size limit"):
        ulb.fetch(tmp_path / "oversized")


def test_runner_reports_only_benchmark_and_replays_model(
    csv_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = ulb.read_csv(csv_path)
    monkeypatch.setattr(ulb_benchmark, "load_pinned", lambda path: data)
    result = ulb_benchmark.run(csv_path, tmp_path / "run")
    assert result["production_eligible"] is False
    assert result["behavioral_compatible"] is False
    assert result["feature_version"] == "ulb-pca-v1"
    assert set(result["validation"]) == {"logistic_regression", "random_forest", "xgboost"}
    restored = joblib.load(tmp_path / "run" / "selected.joblib")
    test = ulb.split_masks(data)["test"]
    assert (
        metrics(
            data.labels[test],
            restored.predict_proba(data.features[test])[:, 1],
            result["threshold"],
        )
        == result["final_test"]
    )
    with pytest.raises(FileExistsError):
        ulb_benchmark.run(csv_path, tmp_path / "run")


def test_quoted_numeric_source_values(tmp_path: Path) -> None:
    source = tmp_path / "quoted.csv"
    with source.open("w", newline="") as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        writer.writerow(ulb.HEADER)
        writer.writerow(row(0, -1, 1))
    data = ulb.read_csv(source)
    assert data.labels.tolist() == [1]
    assert data.features[0, 0] == -1
