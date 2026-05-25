"""Event collector mixin — drains pending events from entities after commit."""

from __future__ import annotations

from src.domain.shared.entities import BaseEntity
from src.domain.shared.events import DomainEvent


def collect_events(*entities: BaseEntity) -> list[DomainEvent]:
    """Drain pending events from all provided entities."""
    events: list[DomainEvent] = []
    for entity in entities:
        events.extend(entity.pending_events)
        entity.clear_events()
    return events
