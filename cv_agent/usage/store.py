from decimal import Decimal
from threading import Lock
from typing import Protocol


class UsageStoreError(RuntimeError):
    pass


class UsageBudgetStore(Protocol):
    def apply_once(self, event_id: str, cost: Decimal) -> Decimal:
        """Apply cost once and return remaining budget."""


class InMemoryUsageBudgetStore:
    def __init__(self, *, total_budget: Decimal, initial_spent: Decimal):
        self._total_budget = total_budget
        self._spent = initial_spent
        self._events: dict[str, Decimal] = {}
        self._lock = Lock()

    def apply_once(self, event_id: str, cost: Decimal) -> Decimal:
        with self._lock:
            if event_id not in self._events:
                self._spent += cost
                self._events[event_id] = self._spent
            return max(Decimal("0"), self._total_budget - self._events[event_id])
