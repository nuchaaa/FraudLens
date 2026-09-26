from types import TracebackType
from typing import Self

from psycopg.errors import UniqueViolation
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.adapters.database.assessments import (
    PostgresAssessmentRepository,
    PostgresModelRepository,
    PostgresRuleRepository,
)
from backend.adapters.database.cases import PostgresFraudCaseRepository
from backend.adapters.database.console import PostgresConsoleRepository
from backend.adapters.database.evaluations import (
    PostgresEvaluationRepository,
    PostgresEvaluationReviewRepository,
)
from backend.adapters.database.history import (
    PostgresAuditRepository,
    PostgresFeedbackRepository,
    PostgresOutboxRepository,
)
from backend.adapters.database.idempotency import PostgresIdempotencyRepository
from backend.adapters.database.identity import PostgresIdentityRepository
from backend.adapters.database.learning import PostgresProfileLearningRepository
from backend.adapters.database.profiles import (
    PostgresCustomerProfileRepository,
    PostgresSnapshotRepository,
)
from backend.adapters.database.transactions import (
    PostgresCustomerRepository,
    PostgresTransactionRepository,
)
from backend.app.shared.errors import (
    ConcurrentUpdate,
    DuplicateCustomer,
    DuplicateTransaction,
    PersistenceConflict,
)
from backend.app.shared.ports import UnitOfWork


class PostgresUnitOfWork:
    """One-shot, explicit-commit UoW. Every other exit rolls back, including failed commits."""

    def __init__(self, engine: Engine) -> None:
        self._session = Session(engine, autoflush=False, expire_on_commit=False, autobegin=False)
        self._entered = False
        self.console = PostgresConsoleRepository(self._session)
        self.evaluations = PostgresEvaluationRepository(self._session)
        self.reviews = PostgresEvaluationReviewRepository(self._session)
        self.learning = PostgresProfileLearningRepository(self._session)
        self.customers = PostgresCustomerRepository(self._session)
        self.transactions = PostgresTransactionRepository(self._session)
        self.profiles = PostgresCustomerProfileRepository(self._session)
        self.snapshots = PostgresSnapshotRepository(self._session)
        self.models = PostgresModelRepository(self._session)
        self.rules = PostgresRuleRepository(self._session)
        self.assessments = PostgresAssessmentRepository(self._session)
        self.cases = PostgresFraudCaseRepository(self._session)
        self.feedback = PostgresFeedbackRepository(self._session)
        self.audit = PostgresAuditRepository(self._session)
        self.outbox = PostgresOutboxRepository(self._session)
        self.idempotency = PostgresIdempotencyRepository(self._session)
        self.identity = PostgresIdentityRepository(self._session)

    def __enter__(self) -> Self:
        if self._entered:
            raise RuntimeError("unit of work cannot be reused")
        self._entered = True
        self._session.begin()
        return self

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            self._session.rollback()
        finally:
            self._session.close()
        if isinstance(exc, IntegrityError):
            if isinstance(exc.orig, UniqueViolation):
                if exc.orig.diag.constraint_name == "uq_evaluation_cases_assessment_id":
                    raise ConcurrentUpdate("evaluation already has a case") from exc
                if exc.orig.diag.constraint_name == "uq_profile_learning_evidence_case_id":
                    raise ConcurrentUpdate("case already used for profile learning") from exc
                if exc.orig.diag.constraint_name == "pk_profiles":
                    raise ConcurrentUpdate("profile already exists") from exc
                if exc.orig.diag.constraint_name == "pk_transactions":
                    raise DuplicateTransaction("transaction ID already exists") from exc
                if exc.orig.diag.constraint_name == "pk_customers":
                    raise DuplicateCustomer("customer ID already exists") from exc
            raise PersistenceConflict("database constraint rejected this unit of work") from exc


def create_unit_of_work(engine: Engine) -> UnitOfWork:
    """Composition boundary and static conformance check for all repository ports."""
    return PostgresUnitOfWork(engine)
