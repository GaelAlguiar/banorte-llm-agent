from decimal import Decimal
from threading import Lock
from typing import Protocol

from azure.core import MatchConditions
from azure.core.exceptions import (
    HttpResponseError,
    ResourceExistsError,
    ResourceNotFoundError,
)


class UsageStoreError(RuntimeError):
    pass


class UsageBudgetStore(Protocol):
    def apply_once(self, event_id: str, cost: Decimal) -> Decimal:
        """Apply cost once and return remaining budget."""


class InMemoryUsageBudgetStore:
    def __init__(self, *, total_budget: Decimal, initial_spent: Decimal):
        self.total_budget = total_budget
        self._spent = initial_spent
        self._events: dict[str, Decimal] = {}
        self._lock = Lock()

    def apply_once(self, event_id: str, cost: Decimal) -> Decimal:
        with self._lock:
            if event_id not in self._events:
                self._spent += cost
                self._events[event_id] = self._spent
            return max(Decimal("0"), self.total_budget - self._events[event_id])


class AzureTableUsageBudgetStore:
    def __init__(self, *, table_client, total_budget: Decimal,
                 initial_spent: Decimal):
        self.table_client = table_client
        self.total_budget = total_budget
        self.initial_spent = initial_spent

    def apply_once(self, event_id: str, cost: Decimal) -> Decimal:
        for _ in range(5):
            try:
                existing = self.table_client.get_entity("usage", event_id)
                return max(
                    Decimal("0"),
                    self.total_budget - Decimal(existing["spent_after"]),
                )
            except ResourceNotFoundError:
                pass
            except HttpResponseError as error:
                if getattr(error, "status_code", None) not in (404, None):
                    raise UsageStoreError("usage ledger read failed") from error
            try:
                try:
                    aggregate = self.table_client.get_entity("usage", "aggregate")
                except ResourceNotFoundError:
                    try:
                        self.table_client.create_entity({
                            "PartitionKey": "usage",
                            "RowKey": "aggregate",
                            "spent": str(self.initial_spent),
                        })
                    except ResourceExistsError:
                        pass
                    aggregate = self.table_client.get_entity("usage", "aggregate")
                spent_after = Decimal(aggregate["spent"]) + cost
                self.table_client.submit_transaction([
                    (
                        "update",
                        {
                            "PartitionKey": "usage",
                            "RowKey": "aggregate",
                            "spent": str(spent_after),
                        },
                        {
                            "etag": aggregate.metadata["etag"],
                            "match_condition": MatchConditions.IfNotModified,
                            "mode": "replace",
                        },
                    ),
                    (
                        "create",
                        {
                            "PartitionKey": "usage",
                            "RowKey": event_id,
                            "spent_after": str(spent_after),
                        },
                    ),
                ])
                return max(Decimal("0"), self.total_budget - spent_after)
            except HttpResponseError as error:
                if getattr(error, "status_code", None) in (409, 412):
                    continue
                raise UsageStoreError("usage transaction failed") from error
        raise UsageStoreError("usage transaction contention")
