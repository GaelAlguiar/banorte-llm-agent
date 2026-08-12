from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from cv_agent.usage.meter import UsageMeter, format_usage_footer
from cv_agent.usage.models import ModelRates, TokenUsage
from cv_agent.usage.store import InMemoryUsageBudgetStore
from cv_agent.usage.store import AzureTableUsageBudgetStore
from azure.core.exceptions import ResourceExistsError
from azure.core.exceptions import ServiceRequestError


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


def test_meter_does_not_lose_answer_when_storage_network_fails():
    class NetworkFailingStore:
        total_budget = Decimal("10")

        def apply_once(self, event_id, cost):
            raise ServiceRequestError("dns timeout")

    result = UsageMeter(
        store=NetworkFailingStore(),
        rates=ModelRates(Decimal("5"), Decimal("0.5"), Decimal("30")),
    ).record(event_id="id", usage=TokenUsage(1, 0, 0, 0, 1))

    assert result.total_tokens == 1
    assert result.available_percent is None


def test_meter_does_not_lose_answer_when_storage_data_is_corrupt():
    class CorruptStore:
        total_budget = Decimal("10")

        def apply_once(self, event_id, cost):
            return Decimal("not-a-number")

    result = UsageMeter(
        store=CorruptStore(),
        rates=ModelRates(Decimal("5"), Decimal("0.5"), Decimal("30")),
    ).record(event_id="id", usage=TokenUsage(1, 0, 0, 0, 1))

    assert result.total_tokens == 1
    assert result.available_percent is None


def test_meter_prices_cache_writes_and_long_context_multiplier():
    class CapturingStore:
        total_budget = Decimal("10")

        def apply_once(self, event_id, cost):
            self.cost = cost
            return Decimal("5")

        def ready(self):
            return True

    store = CapturingStore()
    meter = UsageMeter(
        store=store,
        rates=ModelRates(Decimal("5"), Decimal("0.5"), Decimal("30")),
    )

    meter.record(
        event_id="long",
        usage=TokenUsage(
            273_000, 10_000, 1_000, 100, 274_000,
            cache_write_tokens=20_000,
        ),
    )

    expected_input = (
        Decimal(243_000) * Decimal("5")
        + Decimal(10_000) * Decimal("0.5")
        + Decimal(20_000) * Decimal("5") * Decimal("1.25")
    ) * Decimal("2")
    expected_output = Decimal(1_000) * Decimal("30") * Decimal("1.5")
    assert store.cost == (expected_input + expected_output) / Decimal(1_000_000)


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


def test_azure_store_does_not_access_network_during_app_startup():
    class Table:
        calls = 0

        def create_entity(self, entity):
            self.calls += 1

    table = Table()

    AzureTableUsageBudgetStore(
        table_client=table,
        total_budget=Decimal("10"),
        initial_spent=Decimal("3.28"),
    )

    assert table.calls == 0


def test_azure_store_readiness_requires_write_access():
    class Entity(dict):
        metadata = {"etag": "etag-1"}

    class Table:
        def __init__(self):
            self.updated = None

        def get_entity(self, partition_key, row_key):
            return Entity(spent="3.28")

        def update_entity(self, **kwargs):
            self.updated = kwargs

    table = Table()
    store = AzureTableUsageBudgetStore(
        table_client=table,
        total_budget=Decimal("10"),
        initial_spent=Decimal("3.28"),
    )

    assert store.ready() is True
    assert table.updated["entity"]["spent"] == "3.28"
    assert table.updated["etag"] == "etag-1"
