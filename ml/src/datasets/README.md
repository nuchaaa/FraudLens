synthetic.py authors explicit synthetic source facts; prepare.py replays only available
prior history through production features and creates chronological/customer-separated splits.
Behavioral external data remains unavailable; see dataset-assessment.md.

`ieee_cis.py` reads only the user's hash-pinned IEEE-CIS labeled training CSVs
for a separate, limited noncommercial retrospective benchmark. It validates
row width, IDs, relative time, amount, binary labels and the optional identity
join. The unlabeled competition test files are excluded. Raw rows stay out of Git;
see docs/research/ieee-cis-retrospective-v1-protocol.md and ieee-cis-NOTICE.md.

`ulb.py` adds a hash-pinned ULB v3 fetcher/importer for a separate retrospective benchmark.
Its exact schema, time boundaries and label-independent duplicate exclusions are defined
in docs/research/ulb-benchmark-protocol.md; source notices in ulb-NOTICE.md.
