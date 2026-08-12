import os
from dataclasses import dataclass


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
    parley_file_max_bytes: int = 10_485_760

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
        if (
            self.agent_api_key
            and self.parley_file_bearer_token
            and self.agent_api_key == self.parley_file_bearer_token
        ):
            raise ValueError(
                "parley_file_bearer_token debe ser distinta de agent_api_key"
            )
        if not 1 <= self.parley_file_max_bytes <= 10_485_760:
            raise ValueError(
                "parley_file_max_bytes debe estar entre 1 y 10485760"
            )

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
            parley_file_max_bytes=int(os.getenv(
                "PARLEY_FILE_MAX_BYTES",
                "10485760",
            )),
        )
