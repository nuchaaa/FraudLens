"""Small reproducible synthetic experiment; never promote its model to production."""

import argparse
import hashlib
import json
import platform
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from numpy.typing import NDArray
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from backend.app.features.context import FEATURE_VERSION
from backend.app.features.engine import FEATURE_NAMES
from ml.src.datasets.prepare import PreparedRow, prepare, source_hash, source_json, split
from ml.src.datasets.synthetic import GENERATOR_VERSION, generate

FloatArray = NDArray[np.float64]


def arrays(rows: tuple[PreparedRow, ...]) -> tuple[FloatArray, FloatArray]:
    return np.asarray([r.values for r in rows], dtype=np.float64), np.asarray(
        [r.label for r in rows], dtype=np.float64
    )


def metrics(y: FloatArray, scores: FloatArray, threshold: float) -> dict[str, float | int]:
    if set(y.tolist()) != {0, 1} or len(y) != len(scores):
        raise ValueError("metrics require aligned binary labels with both classes")
    if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError("model scores must be finite and in [0, 1]")
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be in [0, 1]")
    predicted = scores >= threshold
    tn, fp, fn, tp = (int(v) for v in confusion_matrix(y, predicted, labels=[0, 1]).ravel())
    return {
        "n": len(y),
        "positives": int(y.sum()),
        "prevalence": float(y.mean()),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, scores)),
        "pr_auc_average_precision": float(average_precision_score(y, scores)),
        "fpr": fp / (fp + tn),
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
    }


def choose_threshold(y: FloatArray, scores: FloatArray) -> float:
    # Predeclared grid, F1 objective, higher threshold wins ties. Validation only.
    return max(
        (i / 20 for i in range(1, 20)), key=lambda t: (float(metrics(y, scores, t)["f1"]), t)
    )


def fit_candidates(x: FloatArray, y: FloatArray, seed: int) -> dict[str, Any]:
    if set(y.tolist()) != {0, 1}:
        raise ValueError("training requires both classes")
    models = {
        "logistic_regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(class_weight="balanced", max_iter=2000, random_state=seed),
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=120,
            max_depth=6,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=seed,
            n_jobs=1,
        ),
        "xgboost": XGBClassifier(
            n_estimators=120,
            max_depth=3,
            learning_rate=0.05,
            subsample=1.0,
            colsample_bytree=1.0,
            scale_pos_weight=float((y == 0).sum() / y.sum()),
            objective="binary:logistic",
            eval_metric="logloss",
            tree_method="hist",
            n_jobs=1,
            random_state=seed,
        ),
    }
    for model in models.values():
        model.fit(x, y)
    return models


def select_model(
    models: dict[str, Any], x: FloatArray, y: FloatArray
) -> tuple[str, float, dict[str, Any]]:
    results: dict[str, Any] = {}
    for name, model in models.items():
        scores = np.asarray(model.predict_proba(x)[:, 1], dtype=np.float64)
        threshold = choose_threshold(y, scores)
        results[name] = {"threshold": threshold, "metrics": metrics(y, scores, threshold)}
    # Deterministic lexical tie-break; test labels/scores are not accepted here.
    winner = min(
        results, key=lambda name: (-results[name]["metrics"]["pr_auc_average_precision"], name)
    )
    return winner, float(results[winner]["threshold"]), results


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output: Path, *, seed: int = 17, days: int = 100, customers: int = 24) -> dict[str, Any]:
    # Refuse overwrite, including reruns that could silently replace the test record.
    output.mkdir(parents=True, exist_ok=False)
    dataset = generate(seed, days=days, customers=customers)
    rows = prepare(dataset)
    splits = split(rows, days=days)
    (output / "source.json").write_text(source_json(dataset))
    (output / "prepared.json").write_text(json.dumps([asdict(r) for r in rows], default=str))
    x, y = arrays(splits.train)
    models = fit_candidates(x, y, seed)
    winner, threshold, validation = select_model(models, *arrays(splits.validation))
    model = models[winner]
    joblib.dump(model, output / "selected.joblib")  # Only load trusted locally produced artifacts.
    partitions = {}
    for name, part in (("test", splits.test), ("held_out_test", splits.held_out_test)):
        xt, yt = arrays(part)
        scores = np.asarray(model.predict_proba(xt)[:, 1], dtype=np.float64)
        partitions[name] = metrics(yt, scores, threshold)
        (output / f"{name}_predictions.json").write_text(
            json.dumps(
                [
                    {"transaction_id": r.transaction_id, "label": r.label, "score": float(score)}
                    for r, score in zip(part, scores, strict=True)
                ],
                allow_nan=False,
            )
        )
    (output / "splits.json").write_text(
        json.dumps(
            {
                name: [r.transaction_id for r in part]
                for name, part in (
                    ("train", splits.train),
                    ("validation", splits.validation),
                    ("test", splits.test),
                    ("held_out_test", splits.held_out_test),
                )
            }
        )
    )
    files = (
        "source.json",
        "prepared.json",
        "splits.json",
        "selected.joblib",
        "test_predictions.json",
        "held_out_test_predictions.json",
    )
    report = {
        "status": "complete",
        "experiment_version": "synthetic-comparison-v1",
        "synthetic_only": True,
        "production_eligible": False,
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "days": days,
        "customers": customers,
        "source_sha256": source_hash(dataset),
        "feature_version": FEATURE_VERSION,
        "feature_names": FEATURE_NAMES,
        "selection": "highest validation average precision; lexical tie; grid F1 threshold",
        "selected_model": winner,
        "threshold": threshold,
        "validation": validation,
        "final_evaluation": partitions,
        "split_boundaries": {
            "train_end": splits.train_end.isoformat(),
            "validation_end": splits.validation_end.isoformat(),
            "test_label_freeze": splits.test_end.isoformat(),
        },
        "split_sizes": {
            "train": len(splits.train),
            "validation": len(splits.validation),
            "test": len(splits.test),
            "held_out_test": len(splits.held_out_test),
        },
        "training_prevalence": float(y.mean()),
        "models": {
            name: {key: repr(value) for key, value in fitted.get_params().items()}
            for name, fitted in models.items()
        },
        "packages": {
            name: version(name) for name in ("numpy", "scikit-learn", "scipy", "xgboost", "joblib")
        },
        "python": platform.python_version(),
        "platform": platform.platform(),
        "artifacts": {name: digest(output / name) for name in files},
        "code_sha256": {
            str(path): digest(path)
            for directory in (
                Path("ml/src"),
                Path("backend/app/features"),
                Path("backend/app/profile"),
            )
            for path in sorted(directory.rglob("*.py"))
        },
        "lock_sha256": digest(Path("uv.lock")),
        "limitations": [
            "Authored stochastic labels; not measured banking fraud",
            "Static authored bootstrap; no adaptive-profile effectiveness claim",
            "Single currency KZT; one event per customer/day",
            "Held-out customers have pre-experiment synthetic history",
            "No production model selected; no calibration or confidence intervals",
        ],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic-only offline ML comparison")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    result = run(args.output, seed=args.seed)
    print(
        json.dumps(
            {
                "synthetic_only": True,
                "selected_model": result["selected_model"],
                "report": str(args.output / "report.json"),
            }
        )
    )


if __name__ == "__main__":
    main()
