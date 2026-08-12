from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    total_tokens: int
    cache_write_tokens: int = 0


@dataclass(frozen=True)
class ModelGeneration:
    text: str
    usage: TokenUsage | None


@dataclass(frozen=True)
class ModelRates:
    input_per_million: Decimal
    cached_input_per_million: Decimal
    output_per_million: Decimal
    cache_write_multiplier: Decimal = Decimal("1.25")
    long_context_threshold: int = 272_000
    long_input_multiplier: Decimal = Decimal("2")
    long_output_multiplier: Decimal = Decimal("1.5")


@dataclass(frozen=True)
class PublicUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    available_percent: float | None
