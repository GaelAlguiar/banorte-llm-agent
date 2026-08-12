import os
from dataclasses import dataclass


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
                for host in os.getenv("TRUSTED_ATTACHMENT_HOSTS", "").split(",")
                if host.strip()
            ),
        )
