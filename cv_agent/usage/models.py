from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class ModelGeneration:
    text: str
    usage: TokenUsage | None


@dataclass(frozen=True)
class ModelRates:
    input_per_million: Decimal
    cached_input_per_million: Decimal
    output_per_million: Decimal


@dataclass(frozen=True)
class PublicUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    available_percent: float | None
