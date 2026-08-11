from pathlib import Path

import pytest

from cv_agent.config import Settings
from cv_agent.retrieval.factory import build_retrieval
from cv_agent.retrieval.service import HybridCvRetrieval


def test_local_environment_uses_local_retrieval():
    result = build_retrieval(
        Settings(environment="local"),
        Path("knowledge"),
    )

    assert isinstance(result, HybridCvRetrieval)


def test_production_rejects_missing_search_endpoint():
    with pytest.raises(RuntimeError, match="AZURE_SEARCH_ENDPOINT"):
        build_retrieval(
            Settings(
                openai_api_key="key",
                environment="production",
            ),
            Path("knowledge"),
        )


def test_production_rejects_missing_openai_key():
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        build_retrieval(
            Settings(
                azure_search_endpoint="https://search.example.net",
                environment="production",
            ),
            Path("knowledge"),
        )
