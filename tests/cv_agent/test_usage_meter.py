from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from cv_agent.usage.meter import UsageMeter, format_usage_footer
from cv_agent.usage.models import ModelRates, TokenUsage
from cv_agent.usage.store import InMemoryUsageBudgetStore
from cv_agent.usage.store import AzureTableUsageBudgetStore
from azure.core.exceptions import ResourceExistsError


def test_meter_calculates_cost_and_formats_public_result():
    store = InMemoryUsageBudgetStore(
        total_budget=Decimal("10"),
        initial_spent=Decimal("3.28"),
    )
    meter = UsageMeter(
        store=store,
        rates=ModelRates(
            input_per_million=Decimal("5"),
            cached_input_per_million=Decimal("0.5"),
            output_per_million=Decimal("30"),
        ),
    )

    result = meter.record(
        event_id="response-1",
        usage=TokenUsage(1_200, 200, 234, 80, 1_434),
    )

    assert result.total_tokens == 1_434
    assert result.available_percent == 67.1
    assert format_usage_footer(result) == "1,434 tokens · 67.1% disponible"


def test_store_applies_duplicate_event_once_and_is_thread_safe():
    store = InMemoryUsageBudgetStore(
        total_budget=Decimal("10"),
        initial_spent=Decimal("3.28"),
    )

    with ThreadPoolExecutor(max_workers=4) as executor:
        values = list(executor.map(
            lambda _: store.apply_once("same", Decimal("0.25")),
            range(4),
        ))

    assert values == [Decimal("6.47")] * 4


def test_meter_returns_tokens_without_percentage_when_store_fails():
    class FailingStore:
        def apply_once(self, event_id, cost):
            from cv_agent.usage.store import UsageStoreError
            raise UsageStoreError("unavailable")

    meter = UsageMeter(
        store=FailingStore(),
        rates=ModelRates(Decimal("5"), Decimal("0.5"), Decimal("30")),
    )
    result = meter.record(
        event_id="response-1",
        usage=TokenUsage(1, 0, 1, 0, 2),
    )

    assert result.total_tokens == 2
    assert result.available_percent is None
    assert format_usage_footer(result) is None


def test_azure_store_uses_etag_transaction_and_reuses_ledger_event():
    class Entity(dict):
        metadata = {"etag": "etag-1"}

    class Table:
        def __init__(self):
            self.transaction = None
            self.ledger = None

        def create_entity(self, entity):
            raise ResourceExistsError("exists")

        def get_entity(self, partition_key, row_key):
            if row_key == "aggregate":
                return Entity(spent="3.28")
            if self.ledger:
                return self.ledger
            from azure.core.exceptions import ResourceNotFoundError
            raise ResourceNotFoundError("missing")

        def submit_transaction(self, operations):
            self.transaction = operations
            self.ledger = operations[1][1]

    table = Table()
    store = AzureTableUsageBudgetStore(
        table_client=table,
        total_budget=Decimal("10"),
        initial_spent=Decimal("3.28"),
    )

    first = store.apply_once("event-1", Decimal("0.25"))
    second = store.apply_once("event-1", Decimal("0.25"))

    assert first == second == Decimal("6.47")
    assert table.transaction[0][0] == "update"
    assert table.transaction[0][2]["etag"] == "etag-1"
    assert table.transaction[1][0] == "create"
