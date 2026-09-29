"""Offline IEEE-CIS benchmark; never a behavioral or production model."""

import argparse
import json
import platform
from importlib.metadata import version
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from numpy.typing import NDArray

from ml.src.datasets.ieee_cis import (
    CATEGORICAL_FIELDS,
    SOURCE_HASHES,
    SOURCE_URL,
    CisRow,
    load_pinned,
    split_rows,
)
from ml.src.datasets.ulb import sha256
from ml.src.training.experiment import fit_candidates, metrics, select_model

PROTOCOL = Path("docs/research/ieee-cis-retrospective-v1-protocol.md")
FEATURE_VERSION = "ieee-cis-tabular-v1"
FloatArray = NDArray[np.float64]


def category_vocabulary(train: tuple[CisRow, ...]) -> dict[str, dict[str, int]]:
    """Fit deterministic category columns on training rows only."""
    if not train:
        raise ValueError("training rows are required")
    result: dict[str, dict[str, int]] = {}
    offset = 1  # TransactionAmt is column zero.
    for field in CATEGORICAL_FIELDS:
        categories = sorted({str(getattr(row, field)) for row in train})
        result[field] = {category: offset + index for index, category in enumerate(categories)}
        offset += len(categories)
    return result


def arrays(
    rows: tuple[CisRow, ...], vocabulary: dict[str, dict[str, int]]
) -> tuple[FloatArray, FloatArray]:
    width = 1 + sum(len(categories) for categories in vocabulary.values())
    values = np.zeros((len(rows), width), dtype=np.float64)
    labels = np.empty(len(rows), dtype=np.float64)
    for index, row in enumerate(rows):
        values[index, 0] = row.amount
        labels[index] = row.label
        for field in CATEGORICAL_FIELDS:
            column = vocabulary[field].get(str(getattr(row, field)))
            if column is not None:
                values[index, column] = 1.0
    return values, labels


def run(source: Path, output: Path) -> dict[str, Any]:
    data = load_pinned(source)
    parts, train_end, validation_end = split_rows(data)
    vocabulary = category_vocabulary(parts["train"])
    x_train, y_train = arrays(parts["train"], vocabulary)
    x_validation, y_validation = arrays(parts["validation"], vocabulary)
    x_test, y_test = arrays(parts["test"], vocabulary)

    output.mkdir(parents=True, exist_ok=False)
    print("Verified pinned source and chronological partitions; fitting three models.", flush=True)
    models = fit_candidates(x_train, y_train, 17)
    winner, threshold, validation = select_model(models, x_validation, y_validation)
    selected = models[winner]
    joblib.dump(selected, output / "selected.joblib")
    # Model and threshold are frozen before this single test scoring call.
    scores = np.asarray(selected.predict_proba(x_test)[:, 1], dtype=np.float64)
    final = metrics(y_test, scores, threshold)
    (output / "test_predictions.json").write_text(
        json.dumps(
            [
                {"transaction_id": row.transaction_id, "label": row.label, "score": float(score)}
                for row, score in zip(parts["test"], scores, strict=True)
            ],
            allow_nan=False,
        )
    )
    (output / "split_ids.json").write_text(
        json.dumps(
            {name: [row.transaction_id for row in part] for name, part in parts.items()},
            allow_nan=False,
        )
    )
    (output / "category_vocabulary.json").write_text(
        json.dumps(vocabulary, sort_keys=True, allow_nan=False)
    )
    artifacts = (
        "selected.joblib",
        "test_predictions.json",
        "split_ids.json",
        "category_vocabulary.json",
    )
    report: dict[str, Any] = {
        "status": "complete",
        "experiment_version": "ieee-cis-retrospective-v1",
        "feature_version": FEATURE_VERSION,
        "source_url": SOURCE_URL,
        "source_sha256": SOURCE_HASHES,
        "protocol_sha256": sha256(PROTOCOL),
        "seed": 17,
        "production_eligible": False,
        "behavioral_compatible": False,
        "calibrated": False,
        "noncommercial_research_only": True,
        "raw_rows": len(data.rows),
        "identity_rows": data.identity_rows,
        "matched_identity_rows": data.matched_identity_rows,
        "feature_fields": ("TransactionAmt", "ProductCD", "card4", "card6", "DeviceType"),
        "encoded_feature_count": x_train.shape[1],
        "split_offsets": {
            "train_end_exclusive": train_end,
            "validation_end_exclusive": validation_end,
        },
        "split_counts": {
            name: {"rows": len(part), "positives": sum(row.label for row in part)}
            for name, part in parts.items()
        },
        "selection": "highest validation AP; lexical tie; validation grid F1 threshold",
        "selected_model": winner,
        "threshold": threshold,
        "validation": validation,
        "final_test": final,
        "models": {
            name: {key: repr(value) for key, value in model.get_params().items()}
            for name, model in models.items()
        },
        "packages": {
            name: version(name) for name in ("numpy", "scikit-learn", "scipy", "xgboost", "joblib")
        },
        "python": platform.python_version(),
        "platform": platform.platform(),
        "lock_sha256": sha256(Path("uv.lock")),
        "code_sha256": {
            str(path): sha256(path)
            for path in (
                Path("ml/src/datasets/ieee_cis.py"),
                Path("ml/src/datasets/ulb.py"),
                Path("ml/src/training/ieee_cis_benchmark.py"),
                Path("ml/src/training/experiment.py"),
            )
        },
        "local_artifact_sha256": {name: sha256(output / name) for name in artifacts},
        "limitations": [
            "Relative time offsets are not original calendar timestamps",
            "Arrival, decision, feedback and label availability are unknown",
            "No verified stable customer, recipient, currency or trusted admission history",
            "Only five limited raw feature fields; upstream data provenance remains opaque",
            "Retrospective labels do not prove point-in-time detection",
            "One seed and one chronological split; no production threshold or calibration",
        ],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Pinned IEEE-CIS retrospective benchmark only")
    parser.add_argument("--source", required=True, type=Path, help="folder with labeled train CSVs")
    parser.add_argument("--output", required=True, type=Path, help="new ignored local directory")
    args = parser.parse_args()
    result = run(args.source, args.output)
    print(
        json.dumps(
            {
                "selected_model": result["selected_model"],
                "production_eligible": False,
                "report": str(args.output / "report.json"),
            }
        )
    )


if __name__ == "__main__":
    main()
