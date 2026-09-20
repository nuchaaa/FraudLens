class ConcurrentUpdate(ValueError):
    """A persisted aggregate changed since the caller read it."""


class HistoryConflict(ValueError):
    """An attempted write would replace or contradict immutable history."""


class IdempotencyConflict(ValueError):
    """A principal reused a key for a different request."""


class PersistenceConflict(ValueError):
    """A database constraint rejected the complete unit of work."""


class DuplicateTransaction(PersistenceConflict):
    """The immutable transaction ID already exists."""


class DuplicateCustomer(PersistenceConflict):
    """The customer ID already exists."""
