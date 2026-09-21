"""Strict pinned public benchmark ingestion, independent of behavioral history."""

import argparse
import hashlib
import json
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from ml.src.features.ulb import ULB_FEATURE_NAMES, extract_ulb_features

SOURCE_URL = (
    "https://www.kaggle.com/api/v1/datasets/download/mlg-ulb/creditcardfraud?datasetVersionNumber=3"
)
CSV_SHA256 = "76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89"
HEADER = ("Time", *ULB_FEATURE_NAMES, "Class")
MAX_SOURCE_BYTES = 200_000_000


def sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


@dataclass(frozen=True)
class BenchmarkData:
    features: NDArray[np.float64]
    labels: NDArray[np.float64]
    times: NDArray[np.float64]
    source_rows: NDArray[np.int64]
    raw_rows: int
    excluded_duplicate_features: int


def read_csv(path: Path) -> BenchmarkData:
    """Schema validation for fixtures too; real experiments additionally pin the hash."""
    import csv

    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("source exceeds size limit")
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.reader(source)
        if tuple(next(reader, ())) != HEADER:
            raise ValueError("unsupported benchmark header")
        count = 0
        for fields in reader:
            if len(fields) != len(HEADER):
                raise ValueError("benchmark rows require the exact width")
            count += 1
        if not count:
            raise ValueError("benchmark source must not be empty")
    values = np.loadtxt(path, delimiter=",", skiprows=1, dtype=np.float64, ndmin=2, quotechar='"')
    if values.shape[1] != len(HEADER) or not len(values) or not np.isfinite(values).all():
        raise ValueError("benchmark requires nonempty finite rows of the exact width")
    if (values[:, 0] < 0).any() or not np.isin(values[:, -1], [0, 1]).all():
        raise ValueError("invalid event time or class")
    # The same ordered transformation is available for future benchmark-only inference.
    for row in values:
        extract_ulb_features(tuple(float(v) for v in row[1:-1]))
    source_rows = np.arange(2, len(values) + 2, dtype=np.int64)
    order = np.lexsort((source_rows, values[:, 0]))
    ordered = values[order]
    # First chronological feature occurrence; target labels are deliberately excluded.
    _, first = np.unique(ordered[:, 1:-1], axis=0, return_index=True)
    keep = np.sort(first)
    retained = ordered[keep]
    arrays = (retained[:, 1:-1], retained[:, -1], retained[:, 0], source_rows[order][keep])
    for array in arrays:
        array.flags.writeable = False
    return BenchmarkData(*arrays, len(values), len(values) - len(keep))


def load_pinned(path: Path) -> BenchmarkData:
    if sha256(path) != CSV_SHA256:
        raise ValueError("source content hash does not match approved ULB v3 bytes")
    return read_csv(path)


def split_masks(data: BenchmarkData) -> dict[str, NDArray[np.bool_]]:
    masks = {
        "train": data.times < 86400,
        "validation": (data.times >= 86400) & (data.times < 129600),
        "test": data.times >= 129600,
    }
    for name, mask in masks.items():
        if set(data.labels[mask].tolist()) != {0, 1}:
            raise ValueError(f"{name} requires both classes; do not change frozen boundaries")
    return masks


def fetch(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    archive_path = output / "source.zip"
    with (
        urllib.request.urlopen(SOURCE_URL, timeout=60) as response,
        archive_path.open("xb") as dest,
    ):
        count = 0
        while chunk := response.read(1024 * 1024):
            count += len(chunk)
            if count > MAX_SOURCE_BYTES:
                raise ValueError("download exceeds size limit")
            dest.write(chunk)
    with zipfile.ZipFile(archive_path) as archive:
        member = archive.getinfo("creditcard.csv")
        if member.file_size > MAX_SOURCE_BYTES:
            raise ValueError("CSV exceeds size limit")
        # Extract only the named file to a fixed path; never trust archive paths.
        with archive.open(member) as source, (output / "creditcard.csv").open("xb") as dest:
            count = 0
            while chunk := source.read(1024 * 1024):
                count += len(chunk)
                if count > MAX_SOURCE_BYTES:
                    raise ValueError("CSV exceeds size limit")
                dest.write(chunk)
    if sha256(output / "creditcard.csv") != CSV_SHA256:
        raise ValueError("downloaded CSV differs from approved content; do not train")
    (output / "source.json").write_text(
        json.dumps(
            {
                "source_url": SOURCE_URL,
                "csv_sha256": CSV_SHA256,
                "archive_sha256": sha256(archive_path),
                "version": 3,
                "license": "ODbL-1.0 / DbCL-1.0",
                "notice": "ULB / Worldline Credit Card Fraud Detection; "
                "see docs/research/ulb-NOTICE.md",
            },
            indent=2,
        )
        + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch hash-pinned anonymized ULB v3 benchmark")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    fetch(args.output)
    print("Pinned benchmark downloaded; no training or production promotion performed.")


if __name__ == "__main__":
    main()
