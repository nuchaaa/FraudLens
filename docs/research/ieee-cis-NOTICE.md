# IEEE-CIS competition data notice

The retrospective `ieee-cis-tabular-v1` experiment uses data from the
[IEEE-CIS Fraud Detection competition](https://www.kaggle.com/competitions/ieee-fraud-detection/data),
hosted by Kaggle and the IEEE Computational Intelligence Society. The dataset
page lists its license as **Subject to Competition Rules**. The
[competition rules](https://www.kaggle.com/competitions/ieee-fraud-detection/rules)
permit noncommercial research and education for participants and restrict
sharing competition data with nonparticipants. The user reports accepting
those rules through the downloading Kaggle account. This repository has not
independently authenticated that account or any institutional rights.

Only source file hashes, code, methods and aggregate research outcomes may
appear in this repository. Raw CSVs, row IDs, model artifacts and individual
predictions remain local and ignored by Git. This notice does not relicense
competition data under the FraudLens software license or authorize commercial
use, redistribution, deployment or transfer to another person.

Official metadata describes a labeled transaction training file, an optional
identity file joined on `TransactionID`, and an unlabeled competition test
file. `TransactionDT` is a relative time offset. Actual source fields,
availability semantics and performance limits are governed by the frozen
[benchmark protocol](ieee-cis-retrospective-v1-protocol.md). No behavior-v1
profile or production fraud claim follows from the experiment.
