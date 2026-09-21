"""Retrospective anonymized benchmark; incompatible with behavioral serving inputs."""

import argparse
import json
import platform
from importlib.metadata import version
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from ml.src.datasets.ulb import CSV_SHA256, SOURCE_URL, load_pinned, sha256, split_masks
from ml.src.features.ulb import ULB_FEATURE_NAMES, ULB_FEATURE_VERSION
from ml.src.training.experiment import fit_candidates, metrics, select_model

PROTOCOL = Path("docs/research/ulb-benchmark-protocol.md")


def run(source: Path, output: Path) -> dict[str, Any]:
    # Refuse replace-on-rerun and preserve completed measurements.
    output.mkdir(parents=True, exist_ok=False)
    protocol_hash = sha256(PROTOCOL)
    data = load_pinned(source)
    masks = split_masks(data)
    train, validation, test = (masks[name] for name in ("train", "validation", "test"))
    print("Verified source and frozen partitions; fitting three candidates.", flush=True)
    models = fit_candidates(data.features[train], data.labels[train], 17)
    winner, threshold, candidates = select_model(
        models, data.features[validation], data.labels[validation]
    )
    model = models[winner]
    joblib.dump(model, output / "selected.joblib")
    # Selection is finalized before test predictions; no refitting or tuning follows.
    scores = np.asarray(model.predict_proba(data.features[test])[:, 1], dtype=np.float64)
    final = metrics(data.labels[test], scores, threshold)
    (output / "test_predictions.json").write_text(
        json.dumps(
            [
                {"source_row": int(row), "label": int(label), "score": float(score)}
                for row, label, score in zip(
                    data.source_rows[test], data.labels[test], scores, strict=True
                )
            ],
            allow_nan=False,
        )
    )
    (output / "split_rows.json").write_text(
        json.dumps({name: data.source_rows[mask].tolist() for name, mask in masks.items()})
    )
    report = {
        "status": "complete",
        "experiment_version": "ulb-retrospective-v1",
        "seed": 17,
        "synthetic_only": False,
        "production_eligible": False,
        "behavioral_compatible": False,
        "source_url": SOURCE_URL,
        "source_csv_sha256": CSV_SHA256,
        "source_version": 3,
        "notice": "Contains information from ULB / Worldline Credit Card Fraud Detection",
        "dataset_url": "https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud",
        "license_urls": [
            "https://opendatacommons.org/licenses/odbl/1-0/",
            "https://opendatacommons.org/licenses/dbcl/1-0/",
        ],
        "feature_version": ULB_FEATURE_VERSION,
        "feature_names": ULB_FEATURE_NAMES,
        "protocol_sha256": protocol_hash,
        "raw_rows": data.raw_rows,
        "excluded_duplicate_features": data.excluded_duplicate_features,
        "split_counts": {
            name: {"rows": int(mask.sum()), "positives": int(data.labels[mask].sum())}
            for name, mask in masks.items()
        },
        "split_seconds": {"train_end_exclusive": 86400, "validation_end_exclusive": 129600},
        "selection": "highest validation AP; lexical tie; validation grid F1 threshold",
        "selected_model": winner,
        "threshold": threshold,
        "validation": candidates,
        "final_test": final,
        "models": {
            name: {k: repr(v) for k, v in model.get_params().items()}
            for name, model in models.items()
        },
        "packages": {
            name: version(name) for name in ("numpy", "scikit-learn", "scipy", "xgboost", "joblib")
        },
        "python": platform.python_version(),
        "platform": platform.platform(),
        "lock_sha256": sha256(Path("uv.lock")),
        "code_sha256": {
            str(p): sha256(p)
            for directory in (Path("ml/src"), Path("backend/app"))
            for p in sorted(directory.rglob("*.py"))
        },
        "artifacts": {
            name: sha256(output / name)
            for name in ("selected.joblib", "test_predictions.json", "split_rows.json")
        },
        "limitations": [
            "Final labels only; label/arrival availability unknown",
            "Upstream PCA fitting scope unknown",
            "Customer identities/currency/devices/recipients unavailable",
            "No held-out customer or adaptive-profile evaluation possible",
            "Single seed; first-seen feature tuples only; not calibrated",
            "Cannot select a production behavior-v1 model from this benchmark",
        ],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Hash-pinned ULB retrospective benchmark only")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
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
