from collections.abc import Callable

from backend.app.shared.events import DomainEvent, EventType


class InMemoryEventPublisher:
    """Synchronous dispatch; errors propagate for outbox retry. No durability claim."""

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[Callable[[DomainEvent], None]]] = {}

    def subscribe(self, event_type: EventType, handler: Callable[[DomainEvent], None]) -> None:
        handlers = self._handlers.setdefault(event_type, [])
        if handler not in handlers:
            handlers.append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in tuple(self._handlers.get(event.event_type, [])):
            handler(event)
