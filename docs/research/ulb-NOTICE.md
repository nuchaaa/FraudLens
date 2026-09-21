# ULB / Worldline dataset notice

This benchmark contains information from **Credit Card Fraud Detection**, provided by
Machine Learning Group ULB / Worldline, available at
https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud under the
[Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
Contents are listed under the
[Database Contents License (DbCL) 1.0](https://opendatacommons.org/licenses/dbcl/1-0/).

The public Kaggle metadata API identifies dataset ID 310, version 3, owner Machine
Learning Group - ULB and license “Database: Open Database, Contents: Database Contents”.
The extracted source CSV and download archive are identified in ulb-source-manifest.json;
the selected metadata fields and source endpoint are in ulb-source-metadata.json.
Retrieved 2026-09-20. This evidence resolves the previous unreadable-card limitation.
OpenML's generic “Public” label is not used as a replacement license.

Attribution requested by the associated source description:
Andrea Dal Pozzolo, Olivier Caelen, Reid A. Johnson and Gianluca Bontempi (2015),
“Calibrating Probability with Undersampling for Unbalanced Classification”, IEEE CIDM.
[Source description](https://www.openml.org/api/v1/json/data/1597).

No raw dataset rows or trained models are redistributed in this repository. Aggregate
reports retain this attribution and license links. Reproduction/alteration methods are
provided in ml/src/datasets/ulb.py, ml/src/features/ulb.py and
ml/src/training/ulb_benchmark.py: retain the first chronological identical feature tuple,
use the frozen time partitions, and omit Time/Class from model inputs. No extra source
facts are invented. The benchmark protocol describes every modification and exclusion.
Any published derived database remains subject to the ODbL, including its notice,
share-alike and access requirements; this notice does not relicense the source data
under the project's software terms. The method is available locally with these sources.
