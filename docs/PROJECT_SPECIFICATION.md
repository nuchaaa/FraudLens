You are the lead software engineer responsible for building a production-quality portfolio/research project called **FraudLens**.

You have full access to the development environment, terminal, files, package manager, Git repository, and all project files. Work independently. Do not stop to ask unnecessary questions. When something is ambiguous, choose the simplest professional solution consistent with this specification.

Your responsibility is not only to write code, but to leave the project in a clean, runnable, documented state after every working session.

# 1. PROJECT GOAL

Build:

**FraudLens — Explainable Adaptive Behavioral Fraud Detection System**

FraudLens evaluates banking transactions and estimates their fraud risk using:

* customer behavioral history;
* engineered behavioral features;
* deterministic fraud rules;
* machine-learning risk prediction;
* explainability;
* analyst feedback;
* safe behavioral-profile updates.

The key research/engineering idea is:

**How can a fraud-detection system adapt to legitimate changes in customer behavior without allowing fraudulent or extreme one-off transactions to corrupt the customer's behavioral baseline?**

This project should be good enough to:

* present at a university Technopark;
* demonstrate to bank recruiters;
* publish on GitHub as a serious portfolio project;
* later support a research paper.

Do not create a toy CRUD application.

At the same time, do not over-engineer it.

# 2. ARCHITECTURE

Use:

**Modular Monolith + Clean/Hexagonal Architecture + lightweight DDD + internal event-driven architecture.**

Do NOT start with microservices.

Do NOT add Kafka, Kubernetes, Redis, Elasticsearch, MongoDB, Neo4j, Spark, Airflow, or blockchain unless a future requirement clearly justifies them.

The application must be structured so individual modules could later be extracted into services.

High-level modules:

* Transaction
* Customer Profile
* Feature Engine
* Fraud/ML Engine
* Rule Engine
* Risk Aggregation
* Decision Engine
* Explainability
* Fraud Case Management
* Analyst Feedback
* Profile Update Gate
* Audit
* Shared/domain events

Separate infrastructure adapters from domain logic.

The domain layer must not depend directly on FastAPI, SQLAlchemy, XGBoost, PostgreSQL, or frontend concerns.

# 3. DESIGN PATTERNS

Use patterns only where they solve real problems.

Required patterns:

## Adapter Pattern

Use adapters around:

* ML implementation;
* persistence;
* event publishing;
* future external fraud-risk providers.

Example concepts:

FraudModel port
→ XGBoostFraudModelAdapter

EventPublisher port
→ InMemoryEventPublisher
→ future KafkaEventPublisher

CustomerProfileRepository port
→ PostgresCustomerProfileRepository

## Strategy Pattern

Use for:

* ML model strategy;
* risk aggregation;
* potentially profile-update strategies.

Examples:

* MLOnlyRiskStrategy
* RulesOnlyRiskStrategy
* HybridRiskStrategy

## Repository Pattern

Repositories should abstract persistence.

## Specification Pattern

Use for reusable fraud rules such as:

* NewRecipientSpecification
* AmountAnomalySpecification
* UnusualTimeSpecification
* VelocitySpecification

## State Pattern or strict state-transition model

Use for fraud case lifecycle.

Suggested states:

OPEN
UNDER_REVIEW
CONFIRMED_FRAUD
LEGITIMATE
CLOSED

Invalid transitions must be rejected.

## Domain Events / Observer

Use internal events such as:

* TransactionReceived
* RiskEvaluated
* TransactionFlagged
* FraudCaseCreated
* AnalystDecisionMade
* TransactionConfirmedLegitimate
* TransactionConfirmedFraud
* ProfileUpdateRequested
* ProfileUpdated
* ProfileTransactionQuarantined

Initially implement an in-process event bus.

## Transactional Outbox

Persist important domain events in an outbox table as part of the same database transaction.

Do not add Kafka yet.

## Idempotency

Risk-evaluation requests must support an idempotency key so duplicated requests do not create duplicated assessments/cases/events.

# 4. TECHNOLOGY STACK

Backend:

* Python
* FastAPI
* Pydantic
* SQLAlchemy 2
* Alembic
* PostgreSQL

ML/data:

* pandas
* NumPy
* scikit-learn
* XGBoost
* SHAP
* imbalanced-learn where useful

Frontend:

* React
* TypeScript
* Vite

Development:

* uv
* pyproject.toml
* pytest
* Ruff
* mypy
* Docker
* Docker Compose
* GitHub Actions
* pip-audit

Optional later:

* Testcontainers
* MLflow
* Prometheus
* Grafana

Do not add optional systems during early phases unless the core product is already stable.

# 5. PROJECT STRUCTURE

Use approximately:

fraudlens/
├── backend/
│   ├── app/
│   │   ├── transaction/
│   │   ├── profile/
│   │   ├── features/
│   │   ├── fraud/
│   │   ├── rules/
│   │   ├── risk/
│   │   ├── decision/
│   │   ├── explainability/
│   │   ├── cases/
│   │   ├── feedback/
│   │   ├── audit/
│   │   └── shared/
│   ├── api/
│   ├── adapters/
│   │   ├── database/
│   │   ├── ml/
│   │   └── events/
│   └── main.py
│
├── ml/
│   ├── notebooks/
│   ├── src/
│   │   ├── datasets/
│   │   ├── features/
│   │   ├── training/
│   │   ├── evaluation/
│   │   └── explainability/
│   ├── experiments/
│   └── models/
│
├── frontend/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── ml/
│   └── e2e/
├── docs/
│   ├── architecture/
│   ├── adr/
│   └── research/
├── infra/
│   └── migrations/
├── docker-compose.yml
└── README.md

Adjust this structure if necessary, but preserve clear module boundaries.

# 6. CORE DOMAIN MODEL

At minimum implement concepts around:

Customer

Transaction

CustomerBehaviorProfile

ProfileSnapshot

RiskAssessment

RiskReason

FraudCase

AnalystDecision

ModelVersion

RuleVersion

AuditEvent

OutboxEvent

Transaction fields should support approximately:

* transaction_id
* customer_id
* recipient_id
* amount
* currency
* timestamp
* channel
* device_id
* status

Use synthetic IDs.

Do not store real sensitive banking information.

# 7. BEHAVIORAL PROFILE

This is one of the most important components.

Do not rely only on arithmetic mean.

Maintain robust behavioral statistics such as:

* median amount;
* MAD — Median Absolute Deviation;
* p95 amount;
* typical activity hours;
* transaction frequency;
* common categories;
* known recipients;
* short-term behavior;
* long-term behavior.

Support:

Long-term profile
and
Short-term profile.

Example:

long-term:

* median amount over months
* MAD
* p95
* usual hours

short-term:

* median last 30 days
* recent transaction velocity
* recent recipients

Do not let one ₸8,000,000 legitimate car purchase destroy a customer's normal ₸30,000 behavioral baseline.

# 8. PROFILE UPDATE GATE

This must be a first-class domain component.

Possible decisions:

* ACCEPT
* ACCEPT_WITH_LOW_WEIGHT
* QUARANTINE
* REJECT_FROM_PROFILE

Examples:

Normal confirmed ₸30k purchase:
→ ACCEPT

Confirmed legitimate ₸8M vehicle purchase:
→ QUARANTINE or low-weight exceptional event

Confirmed fraudulent transaction:
→ REJECT_FROM_PROFILE

The profile must not blindly learn from every transaction.

This is central to future research.

# 9. FRAUD FEATURES

Build feature engineering as reusable production code.

Training and inference MUST use the same feature logic.

Initial features can include:

* amount
* amount_vs_customer_median
* amount_vs_customer_mean
* robust amount deviation using MAD
* amount_vs_p95
* new_recipient
* recipient_age
* transactions_last_5_min
* transactions_last_10_min
* transactions_last_hour
* unusual transaction hour
* hour deviation from customer activity
* device_changed
* days_since_last_transfer
* recipient transaction velocity
* short_term_vs_long_term_amount_ratio

Create feature versioning.

Every risk assessment must record the feature-version used.

# 10. MACHINE LEARNING

Start with experimental comparison of:

* Logistic Regression
* Random Forest
* XGBoost

Do not assume XGBoost is automatically best.

Evaluate using:

* Precision
* Recall
* F1
* ROC-AUC
* PR-AUC
* False Positive Rate

Do not use accuracy as the main fraud metric.

Handle class imbalance intentionally.

Experiment with appropriate approaches such as:

* class weights;
* undersampling;
* oversampling;
* SMOTE.

Avoid data leakage.

Prefer chronological train/validation/test splitting where time information exists.

Example:

train:
earlier transactions

validation:
later period

test:
latest period

Document why chronological splitting is used.

Training must be offline and separate from online inference.

Do NOT retrain the model whenever an analyst clicks a button.

# 11. ML PORT

Domain/application code should depend on an abstraction approximately like:

FraudModel.predict(features) -> FraudPrediction

Implement adapters for models.

The rest of the application should not care whether the implementation is:

* XGBoost;
* Logistic Regression;
* Random Forest;
* a future neural model;
* a remote model service.

Every prediction must record:

* model version;
* feature version;
* timestamp.

# 12. RULE ENGINE

Implement deterministic fraud rules independently from ML.

Examples:

* large amount anomaly;
* new recipient;
* suspicious transaction velocity;
* blacklisted/simulated suspicious recipient;
* unusual device;
* unusual time.

Rules should produce reason codes.

Example:

AMOUNT_ANOMALY
NEW_RECIPIENT
HIGH_VELOCITY
UNUSUAL_TIME
DEVICE_CHANGED

Do not bury rules inside endpoint functions.

# 13. HYBRID RISK

Support comparison between:

* Rules only
* ML only
* Hybrid

Create a risk aggregation abstraction.

The final architecture should allow experiments comparing all three.

Do not invent arbitrary weights without documenting them.

Start with configurable weights and document the assumptions.

# 14. DECISION ENGINE

Risk score is not the same as fraud verdict.

The model must output risk, not accuse the customer of fraud.

Suggested decisions:

LOW
→ ALLOW

MEDIUM
→ STEP_UP_VERIFICATION

HIGH
→ HOLD_AND_REVIEW

CRITICAL
→ URGENT_REVIEW

The thresholds must be configuration, not hardcoded everywhere.

# 15. EXPLAINABILITY

Use SHAP for supported ML models.

Provide two explanation levels:

Technical:

* feature contributions;
* SHAP values.

Human-readable:

* "Transaction amount is 18.4× higher than the customer's normal amount."
* "This is the first transfer to this recipient."
* "Transaction occurred outside the customer's typical hours."
* "Six transfers occurred within 20 minutes."

The frontend should primarily show human-readable reasons.

The technical SHAP explanation can be available in an advanced/details section.

# 16. FRAUD CASE MANAGEMENT

High-risk transactions should create fraud cases.

A case must show:

* transaction;
* customer behavioral baseline;
* risk score;
* risk level;
* model version;
* triggered rules;
* explanations;
* timestamps;
* analyst status.

Analysts can mark:

* CONFIRMED_FRAUD
* LEGITIMATE
* NEEDS_INVESTIGATION

Analyst decisions must generate domain events and immutable audit entries.

# 17. ANALYST FEEDBACK

Store:

* transaction ID;
* model prediction;
* model version;
* analyst decision;
* analyst ID;
* timestamp;
* explanation/comment where useful.

Feedback becomes future training data.

Do not automatically retrain production.

# 18. FRONTEND REQUIREMENTS

The frontend must be convenient, modern, minimal, and easy to understand during a live demonstration.

Avoid excessive animation or visual clutter.

Target feel:

professional banking fraud analyst console.

Main navigation:

1. Overview
2. Transactions
3. Fraud Cases
4. Customers / Behavior
5. Models
6. System / Audit

## Dashboard

Show:

* transactions today;
* high-risk transactions;
* cases awaiting review;
* confirmed fraud;
* total suspicious amount;
* model health/active version.

Include useful charts but do not overload the screen.

## Transactions page

Table with:

* transaction ID;
* time;
* customer;
* amount;
* recipient;
* risk score;
* risk level;
* decision;
* status.

Support:

* filtering;
* sorting;
* risk-level filter;
* search.

## Transaction Detail

This is the most important demo screen.

Show clearly:

Transaction:

* amount
* recipient
* timestamp
* channel
* device

Risk:

* risk score
* risk level
* action

Behavior comparison:

* customer median
* customer MAD
* p95
* amount ratio
* usual hours
* transaction velocity

Reasons:

* readable explanation cards

SHAP:

* technical contribution visualization

Analyst controls:

* Mark Fraud
* Mark Legitimate
* Needs Investigation

## Customer Behavior Page

Show customer behavioral history.

Useful visualizations:

* amount over time;
* median baseline;
* p95;
* exceptional/quarantined events;
* suspicious events;
* short-term vs long-term baseline.

This page should make the safe adaptive profiling idea visually understandable.

A legitimate one-time ₸8M purchase should appear as an exceptional/quarantined event without massively changing the normal baseline.

## Fraud Case Page

Show:

* case history;
* transaction;
* reason codes;
* model output;
* profile context;
* analyst decisions;
* audit timeline.

## Models Page

Show:

* active model;
* model version;
* metrics;
* feature version;
* training date;
* Precision;
* Recall;
* F1;
* ROC-AUC;
* PR-AUC.

If multiple experiment models exist, provide comparison.

# 19. FRONTEND UX

Make the interface convenient for repeated use.

Required:

* responsive layout;
* clear typography;
* dark/light usability if easy;
* consistent spacing;
* loading states;
* empty states;
* error states;
* confirmation dialog before analyst decisions;
* accessible labels;
* useful tooltips for ML terminology.

Do not create fake decorative widgets that have no value.

Risk colors may be used consistently:

LOW
MEDIUM
HIGH
CRITICAL

but do not rely on color alone.

Include text labels/icons.

# 20. DEMO DATA

Create realistic synthetic banking data.

The demo must include specific scenarios.

Scenario A:
Normal transaction.

Example:
Customer normally spends ₸20k–₸50k.
Current transaction ₸25k to known recipient.
Expected:
low risk.

Scenario B:
Extreme legitimate purchase.

Customer normally spends around ₸30k.
Purchases a vehicle for ₸8M.
Expected:
high anomaly initially;
requires verification/review;
after confirmed legitimate, transaction becomes exceptional/quarantined rather than poisoning normal profile.

Scenario C:
Fraud after large legitimate purchase.

After the ₸8M car purchase:
fraudulent ₸500k transfer to new recipient.

Expected:
system should still see the ₸500k transfer as suspicious because robust baseline was not destroyed.

Scenario D:
Gradual legitimate behavior change.

Customer gradually changes from normal spending around ₸30k to ₸100k+ across many confirmed legitimate transactions.

Expected:
profile should gradually adapt.

Scenario E:
Potential profile-poisoning attack.

Series:
₸50k
₸70k
₸100k
₸150k
₸250k
₸500k

Expected:
system should not blindly adapt enough to make increasing fraudulent amounts normal.

These scenarios are extremely important for the future research paper.

# 21. SECURITY

Implement sensible security.

At minimum:

* authentication;
* role-based authorization;
* roles such as ANALYST, ADMIN, SERVICE;
* password hashing with Argon2 or appropriate secure library;
* JWT-based session/API authentication if suitable;
* input validation;
* safe database queries through ORM;
* secrets from environment;
* never commit secrets;
* audit important actions.

Do not store:

* real card numbers;
* passports;
* real personal information.

Use synthetic identifiers.

# 22. AUDITABILITY

Important decisions must be explainable later.

Every risk assessment should include:

* transaction ID;
* model version;
* feature version;
* rule version;
* risk score;
* reason codes;
* decision;
* timestamp.

Analyst actions should be immutable audit records.

Do not silently overwrite historical decisions.

# 23. MODEL VERSIONING

Track models in DB metadata.

Example:

model_version:
xgb-2026-01-v1

metrics:
precision
recall
F1
PR-AUC
ROC-AUC

status:
CANDIDATE
PRODUCTION
ARCHIVED

Initially model files can be stored locally under controlled model directories.

Do not introduce MLflow until it becomes useful.

# 24. TESTING

Tests are mandatory.

Create:

## Unit tests

Examples:

* fraud transaction does not update normal profile;
* exceptional transaction is quarantined;
* amount anomaly rule works;
* invalid fraud-case transitions fail;
* hybrid risk aggregation works;
* duplicate idempotency keys are handled.

## Integration tests

Test:

FastAPI
+
PostgreSQL
+
repositories
+
risk evaluation flow.

## ML tests

Test:

* required features exist;
* feature ordering/schema remains stable;
* model loads;
* predictions fall within expected range;
* model version exists;
* inference handles malformed input safely.

## End-to-end tests

At least one important user flow:

transaction submission
→ risk evaluation
→ case creation
→ analyst decision
→ profile update decision.

# 25. QUALITY

Use:

* Ruff
* mypy
* pytest
* pip-audit

Prefer type hints.

Avoid huge files.

Avoid duplicated business logic.

Avoid circular dependencies.

Do not swallow exceptions.

Create structured logging.

# 26. DOCKER

The project should eventually run with approximately:

docker compose up

Services initially:

* backend
* frontend
* postgres

Do not add unnecessary infrastructure.

# 27. GITHUB ACTIONS

Create CI that runs:

1. lint;
2. type checking;
3. tests;
4. security/dependency checks;
5. build validation.

# 28. DOCUMENTATION

The README must be recruiter-friendly.

README sections:

* What is FraudLens?
* Problem
* Why behavioral fraud detection?
* Key idea: safe adaptive profiling
* Architecture
* Screenshots
* Demo scenarios
* Tech stack
* ML methodology
* Metrics
* API
* How to run
* Testing
* Security
* Limitations
* Research direction
* Roadmap

Create architecture diagrams using Mermaid.

Create C4-style diagrams where useful.

# 29. ARCHITECTURE DECISION RECORDS

Create docs/adr/.

At minimum:

ADR-001-modular-monolith.md
ADR-002-hexagonal-architecture.md
ADR-003-postgresql.md
ADR-004-xgboost-baseline.md
ADR-005-event-driven-internals.md
ADR-006-safe-profile-update.md

Each ADR should explain:

Context
Decision
Alternatives
Why alternatives were rejected
Consequences

# 30. RESEARCH DOCUMENTATION

Create docs/research/.

Maintain notes covering:

Research question:

"How can adaptive behavioral fraud detection learn legitimate behavioral changes without allowing anomalous or fraudulent transactions to poison the customer's behavioral profile?"

Potential experiment comparison:

A. Mean-based baseline
B. Median/MAD robust baseline
C. Naive adaptive baseline
D. Safe adaptive baseline with profile-update gate

Potential scenarios:

* normal behavior;
* legitimate spending outlier;
* fraud after legitimate outlier;
* genuine concept drift;
* gradual profile poisoning.

Do not fabricate experimental results.

Only write metrics after running actual experiments.

# 31. IMPLEMENTATION ORDER

Work in phases.

PHASE 0 — Repository foundation

* inspect current repository;
* initialize structure if necessary;
* configure uv;
* pyproject.toml;
* linting;
* typing;
* testing;
* environment configuration;
* PostgreSQL/Docker foundation;
* README skeleton;
* ADR skeleton.

PHASE 1 — Domain

Implement core domain entities and value objects.

No complex ML yet.

PHASE 2 — Persistence

PostgreSQL
SQLAlchemy
Alembic
repositories.

PHASE 3 — Transaction API

Submit and retrieve synthetic transactions.

Add idempotency.

PHASE 4 — Customer behavior

Implement:

* profile;
* median;
* MAD;
* p95;
* short-term profile;
* long-term profile.

PHASE 5 — Feature Engine

Implement production feature extraction.

PHASE 6 — Rule Engine

Implement specifications/rules and reason codes.

PHASE 7 — ML experiment

Prepare dataset.

Train:

* Logistic Regression;
* Random Forest;
* XGBoost.

Evaluate properly.

Select production baseline based on metrics, not assumption.

PHASE 8 — Inference

Integrate chosen model through FraudModel adapter.

PHASE 9 — Risk + Decision

Hybrid risk aggregation.

Decision engine.

PHASE 10 — Explainability

SHAP
+
human-readable reason generation.

PHASE 11 — Cases / Feedback

Fraud case workflow.

Analyst feedback.

Audit.

PHASE 12 — Safe Adaptive Profile Update

Implement Profile Update Gate.

Handle:

* normal;
* exceptional legitimate;
* confirmed fraud;
* gradual legitimate behavior change.

PHASE 13 — Internal Events / Outbox

Domain events.

In-memory event dispatcher.

Transactional outbox.

PHASE 14 — Frontend

Build polished analyst dashboard.

PHASE 15 — Security

Authentication
RBAC
security review.

PHASE 16 — Demo Scenarios

Create deterministic synthetic demo data for the five key scenarios.

PHASE 17 — Research Experiments

Compare profiling strategies and create reproducible experiment scripts.

PHASE 18 — Polish

README
architecture diagrams
screenshots
tests
Docker
CI
cleanup.

# 32. CRITICAL WORKING RULE: CHECKPOINT YOURSELF

This is mandatory.

You may not finish the entire project in one execution/context window.

Therefore maintain these files at the repository root:

## PROJECT_STATUS.md

Update this continuously.

It must contain:

* current phase;
* completed work;
* partially completed work;
* tests currently passing/failing;
* important architecture decisions;
* important file locations;
* known bugs;
* unresolved technical debt;
* exact next tasks.

Use checkboxes.

Example:

## Phase 4 — Customer Profiles

[x] Profile domain model
[x] Median calculation
[x] MAD calculation
[ ] Short-term profile
[ ] Profile snapshots
[ ] Tests for extreme outlier behavior

## NEXT_SESSION_PROMPT.md

Before ending any working session, overwrite this file with a ready-to-use prompt for your future self.

The prompt must include:

* project goal;
* current architecture;
* exact current phase;
* what was completed;
* what remains;
* important filenames;
* commands needed;
* failing tests if any;
* what should be done first next time.

It must be sufficiently detailed that a fresh model with no previous conversation can continue immediately.

Example format:

"Continue implementing FraudLens.

Current phase: Phase 4 — Customer Behavior.

Completed:
...

Current tests:
...

Important files:
...

Next task:
1.
2.
3.

Do not redo completed work.
Read PROJECT_STATUS.md first."

## SESSION_LOG.md

Append a short entry for each substantial session:

date/time if available;
work performed;
decisions;
tests;
next step.

Do not store hidden chain-of-thought or private reasoning.

Only store concise engineering decisions and factual progress.

# 33. BEFORE YOU STOP

Before stopping for ANY reason:

1. Run relevant tests.
2. Run lint/type checks where practical.
3. Update PROJECT_STATUS.md.
4. Update NEXT_SESSION_PROMPT.md.
5. Update SESSION_LOG.md.
6. Ensure unfinished code is not left in a silently broken state.
7. Clearly report what works and what does not.

If tests fail, record the exact failure and next fix.

Do not claim something works unless it was actually checked.

# 34. RESULT TO RETURN TO ME

At the end of each execution, report:

## Completed

Concise summary.

## Current architecture/state

What now exists.

## Tests

Exact result.

## How to run

Exact commands.

## Important files

Main files added/changed.

## Remaining

What is not implemented yet.

## Next step

The exact next engineering task.

## Continue prompt

Paste the contents of NEXT_SESSION_PROMPT.md so I can give it back to you if necessary.

# 35. AUTONOMY

You have full access.

Use the terminal.

Inspect files.

Create folders.

Install dependencies.

Run migrations.

Run tests.

Fix errors.

Do not merely tell me what code I should write.

Implement it.

If a dependency or approach causes problems, debug it and choose a sensible alternative.

Do not stop after generating scaffolding.

Continue until you reach a natural tested checkpoint.

Do not ask me to confirm ordinary engineering decisions already defined in this specification.

# 36. ENGINEERING PHILOSOPHY

The priority order is:

1. Correctness
2. Clear architecture
3. Security
4. Testability
5. Maintainability
6. Good UX
7. Research reproducibility
8. Scalability
9. Performance optimization

Do not optimize prematurely.

Do not introduce distributed systems simply to appear advanced.

A clean modular monolith with excellent boundaries is better than seven broken microservices.

# 37. FIRST ACTION

Start by inspecting the current repository/environment.

Then:

1. Determine what already exists.
2. Do not destroy useful existing work.
3. Create or update PROJECT_STATUS.md.
4. Create the architecture skeleton.
5. Complete Phase 0 properly.
6. Continue into Phase 1 if Phase 0 is stable.
7. Run tests/checks.
8. Leave a complete continuation checkpoint.

Begin implementation now.
