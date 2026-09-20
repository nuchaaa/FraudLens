from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import joblib
import numpy as np
import pytest

from backend.app.features.engine import FEATURE_NAMES
from ml.src.datasets.prepare import prepare, source_hash, split
from ml.src.datasets.synthetic import START, LabeledEvent, SyntheticDataset, generate
from ml.src.training.experiment import (
    arrays,
    choose_threshold,
    fit_candidates,
    metrics,
    run,
    select_model,
)


@pytest.fixture(scope="module")
def dataset() -> SyntheticDataset:
    return generate(17, days=60, customers=12)


def test_reproducible_source_and_features(dataset: SyntheticDataset) -> None:
    assert source_hash(dataset) == source_hash(generate(17, days=60, customers=12))
    assert source_hash(dataset) != source_hash(generate(18, days=60, customers=12))
    rows = prepare(dataset)
    inverted = replace(dataset, events=tuple(replace(e, label=1 - e.label) for e in dataset.events))
    # Future/evaluation targets cannot authorize profile updates or change any feature.
    assert [r.values for r in rows] == [r.values for r in prepare(inverted)]
    assert all(len(r.values) == 29 and np.isfinite(r.values).all() for r in rows)


def test_future_arrival_excluded_and_label_delays(dataset: SyntheticDataset) -> None:
    candidate = dataset.events[0]
    tx = replace(
        candidate.transaction,
        transaction_id=dataset.events[1].transaction.transaction_id,
        timestamp=candidate.transaction.timestamp - timedelta(minutes=1),
    )
    early = LabeledEvent(tx, tx.timestamp, candidate.label_available_at, 0)
    late = replace(early, available_at=candidate.available_at + timedelta(hours=1))

    def candidate_row(event: LabeledEvent) -> tuple[float, ...]:
        rows = prepare(replace(dataset, events=(event, candidate)))
        return next(
            r.values for r in rows if r.transaction_id == str(candidate.transaction.transaction_id)
        )

    velocity_index = FEATURE_NAMES.index("transactions_last_5_min")
    assert candidate_row(early)[velocity_index] == 1
    assert candidate_row(late)[velocity_index] == 0


def test_split_customer_time_and_label_isolation(dataset: SyntheticDataset) -> None:
    parts = split(prepare(dataset), days=dataset.days)
    assert max(r.label_available_at for r in parts.train) < parts.train_end
    assert min(r.event_at for r in parts.validation) >= parts.train_end
    assert max(r.label_available_at for r in parts.validation) < parts.validation_end
    assert min(r.event_at for r in parts.test) >= parts.validation_end
    assert not {r.customer_id for r in parts.train + parts.validation} & {
        r.customer_id for r in parts.held_out_test
    }
    ids = [
        {r.transaction_id for r in part}
        for part in (parts.train, parts.validation, parts.test, parts.held_out_test)
    ]
    assert sum(map(len, ids)) == len(set.union(*ids))


def test_bad_sources_fail(dataset: SyntheticDataset) -> None:
    with pytest.raises(ValueError, match="duplicate source transaction"):
        prepare(replace(dataset, events=(dataset.events[0], dataset.events[0])))
    with pytest.raises(ValueError, match="duplicate source profile"):
        prepare(replace(dataset, profiles=(dataset.profiles[0], dataset.profiles[0])))
    with pytest.raises(ValueError, match="bootstrap"):
        prepare(
            replace(
                dataset,
                profiles=tuple(
                    replace(p, as_of=START + timedelta(days=1)) for p in dataset.profiles
                ),
            )
        )
    with pytest.raises(ValueError, match="both classes"):
        split(
            prepare(replace(dataset, events=tuple(replace(e, label=0) for e in dataset.events))),
            days=dataset.days,
        )
    for updates in (
        {"label": 2},
        {"available_at": START - timedelta(days=1)},
        {"label_available_at": START - timedelta(days=1)},
    ):
        with pytest.raises(ValueError):
            replace(dataset.events[0], **updates)


def test_metrics_known_confusion_and_threshold() -> None:
    y = np.asarray([0.0, 0.0, 1.0, 1.0])
    scores = np.asarray([0.1, 0.6, 0.4, 0.9])
    result = metrics(y, scores, 0.5)
    assert [result[k] for k in ("tn", "fp", "fn", "tp")] == [1, 1, 1, 1]
    assert result["fpr"] == result["precision"] == result["recall"] == 0.5
    assert choose_threshold(y, scores) == 0.4
    with pytest.raises(ValueError):
        metrics(y, np.asarray([0.1, 0.6, 0.4, np.nan]), 0.5)
    with pytest.raises(ValueError):
        metrics(np.zeros(4), scores, 0.5)


def test_fit_uses_train_scaler_and_validation_only(dataset: SyntheticDataset) -> None:
    parts = split(prepare(dataset), days=dataset.days)
    x, y = arrays(parts.train)
    models = fit_candidates(x, y, 17)
    np.testing.assert_allclose(models["logistic_regression"][0].mean_, x.mean(axis=0))
    first = select_model(models, *arrays(parts.validation))
    # Changing the separate test targets cannot affect selection (not an input).
    altered = replace(parts, test=tuple(replace(r, label=1 - r.label) for r in parts.test))
    assert select_model(models, *arrays(altered.validation)) == first
    assert set(first[2]) == {"logistic_regression", "random_forest", "xgboost"}


def test_end_to_end_artifacts_and_reload(tmp_path: Path, dataset: SyntheticDataset) -> None:
    output = tmp_path / "experiment"
    result = run(output, seed=17, days=60, customers=12)
    assert result["production_eligible"] is False
    assert result["synthetic_only"] is True
    assert result["source_sha256"] == source_hash(dataset)
    restored = joblib.load(output / "selected.joblib")  # Only this test's own model.
    xt, yt = arrays(split(prepare(dataset), days=60).test)
    scores = restored.predict_proba(xt)[:, 1]
    assert metrics(yt, scores, result["threshold"]) == result["final_evaluation"]["test"]
    with pytest.raises(FileExistsError):
        run(output)
