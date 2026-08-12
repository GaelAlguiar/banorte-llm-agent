import os
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


MIN_REQUEST_BODY_BYTES = 65_536
DEFAULT_MAX_REQUEST_BODY_BYTES = 1_048_576
MAX_REQUEST_BODY_BYTES = 2_097_152


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None = None
    agent_api_key: str | None = None
    model: str = "gpt-5.6"
    privacy_classifier_model: str | None = None
    professional_classifier_model: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    azure_search_endpoint: str | None = None
    azure_search_index: str = "cv-profile-v1"
    azure_search_min_score: float = 0.03
    environment: str = "local"
    max_attachments: int = 4
    trusted_attachment_hosts: tuple[str, ...] = ()
    max_request_body_bytes: int = DEFAULT_MAX_REQUEST_BODY_BYTES
    parley_file_base_url: str | None = None
    parley_file_bearer_token: str | None = None
    parley_file_capability_scope: str | None = None
    parley_file_max_bytes: int = 10_485_760
    usage_meter_enabled: bool = False
    usage_storage_account: str | None = None
    usage_storage_table: str | None = None
    usage_total_budget: str | None = None
    usage_initial_spent: str | None = None
    usage_input_rate: str | None = None
    usage_cached_input_rate: str | None = None
    usage_output_rate: str | None = None

    def __post_init__(self) -> None:
        if not (
            MIN_REQUEST_BODY_BYTES
            <= self.max_request_body_bytes
            <= MAX_REQUEST_BODY_BYTES
        ):
            raise ValueError(
                "max_request_body_bytes debe estar entre "
                f"{MIN_REQUEST_BODY_BYTES} y {MAX_REQUEST_BODY_BYTES}"
            )
        if bool(self.parley_file_base_url) != bool(self.parley_file_bearer_token):
            raise ValueError(
                "parley_file_base_url y parley_file_bearer_token deben configurarse juntos"
            )
        if self.parley_file_base_url and self.parley_file_capability_scope != "agent-files":
            raise ValueError(
                "parley_file_capability_scope debe ser agent-files"
            )
        if not self.parley_file_base_url and self.parley_file_capability_scope:
            raise ValueError(
                "parley_file_capability_scope requiere un resolver configurado"
            )
        if (
            self.parley_file_bearer_token
            and self.parley_file_bearer_token in {
                self.agent_api_key,
                self.openai_api_key,
            }
        ):
            raise ValueError(
                "parley_file_bearer_token debe ser distinta de las demás claves"
            )
        if not 1 <= self.parley_file_max_bytes <= 10_485_760:
            raise ValueError(
                "parley_file_max_bytes debe estar entre 1 y 10485760"
            )
        if self.usage_meter_enabled:
            required = (
                self.usage_storage_account, self.usage_storage_table,
                self.usage_total_budget, self.usage_initial_spent,
                self.usage_input_rate, self.usage_cached_input_rate,
                self.usage_output_rate,
            )
            if not all(required):
                raise ValueError("usage meter requiere configuración completa")
            if not re.fullmatch(r"[a-z0-9]{3,24}", self.usage_storage_account):
                raise ValueError("usage storage account inválida")
            if not re.fullmatch(
                r"[A-Za-z][A-Za-z0-9]{2,62}",
                self.usage_storage_table,
            ):
                raise ValueError("usage storage table inválida")
            try:
                total = Decimal(self.usage_total_budget)
                spent = Decimal(self.usage_initial_spent)
                rates = tuple(Decimal(value) for value in (
                    self.usage_input_rate,
                    self.usage_cached_input_rate,
                    self.usage_output_rate,
                ))
            except (InvalidOperation, TypeError) as error:
                raise ValueError("usage configuration inválida") from error
            decimals = (total, spent, *rates)
            if (
                not all(value.is_finite() for value in decimals)
                or total <= 0
                or spent < 0
                or spent > total
                or any(rate <= 0 for rate in rates)
            ):
                raise ValueError("usage configuration fuera de rango")

    @property
    def usage_initial_available_percent(self) -> float | None:
        if not self.usage_meter_enabled:
            return None
        total = Decimal(self.usage_total_budget)
        spent = Decimal(self.usage_initial_spent)
        return float((total - spent) / total * Decimal("100"))

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            agent_api_key=os.getenv("AGENT_API_KEY") or None,
            model=os.getenv("OPENAI_MODEL", "gpt-5.6"),
            privacy_classifier_model=(
                os.getenv("OPENAI_PRIVACY_CLASSIFIER_MODEL") or None
            ),
            professional_classifier_model=(
                os.getenv("OPENAI_PROFESSIONAL_CLASSIFIER_MODEL") or None
            ),
            embedding_model=os.getenv(
                "EMBEDDING_MODEL",
                "text-embedding-3-small",
            ),
            embedding_dimensions=int(
                os.getenv("EMBEDDING_DIMENSIONS", "1536")
            ),
            azure_search_endpoint=(
                os.getenv("AZURE_SEARCH_ENDPOINT") or None
            ),
            azure_search_index=os.getenv(
                "AZURE_SEARCH_INDEX",
                "cv-profile-v1",
            ),
            azure_search_min_score=float(
                os.getenv("AZURE_SEARCH_MIN_SCORE", "0.03")
            ),
            environment=os.getenv("APP_ENV", "local"),
            max_attachments=int(os.getenv("MAX_ATTACHMENTS", "4")),
            trusted_attachment_hosts=tuple(
                host.strip()
                for host in os.getenv(
                    "ATTACHMENT_TRUSTED_HOSTS", ""
                ).split(",")
                if host.strip()
            ),
            max_request_body_bytes=int(os.getenv(
                "MAX_REQUEST_BODY_BYTES",
                str(DEFAULT_MAX_REQUEST_BODY_BYTES),
            )),
            parley_file_base_url=os.getenv("PARLEY_FILE_BASE_URL") or None,
            parley_file_bearer_token=(
                os.getenv("PARLEY_FILE_BEARER_TOKEN") or None
            ),
            parley_file_capability_scope=(
                os.getenv("PARLEY_FILE_CAPABILITY_SCOPE") or None
            ),
            parley_file_max_bytes=int(os.getenv(
                "PARLEY_FILE_MAX_BYTES",
                "10485760",
            )),
            usage_meter_enabled=(
                os.getenv("USAGE_METER_ENABLED", "false").lower() == "true"
            ),
            usage_storage_account=os.getenv("USAGE_STORAGE_ACCOUNT") or None,
            usage_storage_table=os.getenv("USAGE_STORAGE_TABLE") or None,
            usage_total_budget=os.getenv("USAGE_TOTAL_BUDGET") or None,
            usage_initial_spent=os.getenv("USAGE_INITIAL_SPENT") or None,
            usage_input_rate=os.getenv("USAGE_INPUT_RATE") or None,
            usage_cached_input_rate=os.getenv("USAGE_CACHED_INPUT_RATE") or None,
            usage_output_rate=os.getenv("USAGE_OUTPUT_RATE") or None,
        )
