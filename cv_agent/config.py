import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None = None
    agent_api_key: str | None = None
    model: str = "gpt-5.6"
    embedding_model: str = "text-embedding-3-small"
    environment: str = "local"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            agent_api_key=os.getenv("AGENT_API_KEY") or None,
            model=os.getenv("OPENAI_MODEL", "gpt-5.6"),
            embedding_model=os.getenv(
                "EMBEDDING_MODEL",
                "text-embedding-3-small",
            ),
            environment=os.getenv("APP_ENV", "local"),
        )
