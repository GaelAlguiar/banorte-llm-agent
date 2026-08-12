from decimal import Decimal, ROUND_HALF_UP
from azure.core.exceptions import AzureError

from cv_agent.observability.logging import log_event
from cv_agent.usage.models import ModelRates, PublicUsage, TokenUsage
from cv_agent.usage.store import UsageBudgetStore, UsageStoreError


_MILLION = Decimal("1000000")


class UsageMeter:
    def __init__(self, *, store: UsageBudgetStore, rates: ModelRates,
                 total_budget: Decimal | None = None):
        self.store = store
        self.rates = rates
        self.total_budget = total_budget or getattr(store, "total_budget", None)

    def record(self, *, event_id: str, usage: TokenUsage) -> PublicUsage:
        uncached = (
            usage.input_tokens
            - usage.cached_input_tokens
            - usage.cache_write_tokens
        )
        input_multiplier = (
            self.rates.long_input_multiplier
            if usage.input_tokens > self.rates.long_context_threshold
            else Decimal("1")
        )
        output_multiplier = (
            self.rates.long_output_multiplier
            if usage.input_tokens > self.rates.long_context_threshold
            else Decimal("1")
        )
        input_cost = (
            Decimal(uncached) * self.rates.input_per_million
            + Decimal(usage.cached_input_tokens) * self.rates.cached_input_per_million
            + Decimal(usage.cache_write_tokens)
            * self.rates.input_per_million * self.rates.cache_write_multiplier
        ) * input_multiplier
        output_cost = (
            Decimal(usage.output_tokens)
            * self.rates.output_per_million
            * output_multiplier
        )
        cost = (input_cost + output_cost) / _MILLION
        try:
            remaining = self.store.apply_once(event_id, cost)
            if not self.total_budget:
                raise UsageStoreError("missing total budget")
            percent = (remaining / self.total_budget * Decimal("100")).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP,
            )
            available = float(min(Decimal("100"), max(Decimal("0"), percent)))
        except (UsageStoreError, AzureError):
            available = None
            log_event(
                "usage_meter",
                status="error",
                error_type="usage_store_error",
            )
        return PublicUsage(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            available_percent=available,
        )

    def ready(self) -> bool:
        try:
            return self.store.ready()
        except (UsageStoreError, AzureError):
            return False


def format_usage_footer(usage: PublicUsage) -> str | None:
    if usage.available_percent is None:
        return None
    return f"{usage.total_tokens:,} tokens · {usage.available_percent:.1f}% disponible"
