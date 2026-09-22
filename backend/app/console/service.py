from datetime import UTC, datetime
from uuid import UUID

from backend.app.console.contracts import ConsoleSummary, WorklistCursor, WorklistPage
from backend.app.shared.security import Principal, Role
from backend.app.transaction.service import UnitOfWorkFactory


class ConsoleService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self.uow_factory = uow_factory

    @staticmethod
    def _scope(principal: Principal) -> frozenset[UUID] | None:
        return None if Role.ADMIN in principal.roles else principal.customer_ids

    def worklist(
        self, principal: Principal, *, limit: int, cursor: WorklistCursor | None
    ) -> WorklistPage:
        if not 1 <= limit <= 100:
            raise ValueError("worklist limit must be between 1 and 100")
        with self.uow_factory() as uow:
            return uow.console.worklist(self._scope(principal), limit=limit, cursor=cursor)

    def summary(self, principal: Principal) -> ConsoleSummary:
        with self.uow_factory() as uow:
            return uow.console.summary(self._scope(principal), as_of=datetime.now(UTC))
