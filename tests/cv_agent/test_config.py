import pytest

from cv_agent.config import Settings


def test_settings_use_safe_search_defaults(monkeypatch):
    monkeypatch.delenv("AZURE_SEARCH_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_SEARCH_INDEX", raising=False)
    monkeypatch.delenv("AZURE_SEARCH_MIN_SCORE", raising=False)

    settings = Settings.from_env()

    assert settings.azure_search_endpoint is None
    assert settings.azure_search_index == "cv-profile-v1"
    assert settings.azure_search_min_score == 0.03
    assert settings.embedding_dimensions == 1536


def test_settings_read_azure_search_values(monkeypatch):
    monkeypatch.setenv(
        "AZURE_SEARCH_ENDPOINT",
        "https://search.example.net",
    )
    monkeypatch.setenv("AZURE_SEARCH_INDEX", "profile-test")
    monkeypatch.setenv("AZURE_SEARCH_MIN_SCORE", "0.07")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "512")

    settings = Settings.from_env()

    assert settings.azure_search_endpoint == "https://search.example.net"
    assert settings.azure_search_index == "profile-test"
    assert settings.azure_search_min_score == 0.07
    assert settings.embedding_dimensions == 512


def test_settings_read_professional_classifier_model(monkeypatch):
    monkeypatch.setenv("OPENAI_PROFESSIONAL_CLASSIFIER_MODEL", "intent-model")

    assert Settings.from_env().professional_classifier_model == "intent-model"


def test_attachment_policy_reads_environment(monkeypatch):
    monkeypatch.setenv("MAX_ATTACHMENTS", "2")
    monkeypatch.setenv(
        "ATTACHMENT_TRUSTED_HOSTS",
        "uploads.example.com, signed.example.net",
    )

    settings = Settings.from_env()

    assert settings.max_attachments == 2
    assert settings.trusted_attachment_hosts == (
        "uploads.example.com", "signed.example.net",
    )


def test_parley_resolver_reads_dedicated_optional_secret(monkeypatch):
    monkeypatch.setenv(
        "PARLEY_FILE_BASE_URL",
        "https://portal.example.com/reto-ia/api/files",
    )
    monkeypatch.setenv("PARLEY_FILE_BEARER_TOKEN", "separate-secret")
    monkeypatch.setenv("PARLEY_FILE_CAPABILITY_SCOPE", "agent-files")
    monkeypatch.setenv("PARLEY_FILE_MAX_BYTES", "10485760")

    settings = Settings.from_env()

    assert settings.parley_file_base_url.endswith("/api/files")
    assert settings.parley_file_bearer_token == "separate-secret"
    assert settings.parley_file_capability_scope == "agent-files"
    assert settings.parley_file_max_bytes == 10_485_760


def test_parley_resolver_requires_base_and_secret_together():
    with pytest.raises(ValueError, match="parley"):
        Settings(parley_file_base_url="https://portal.example.com/api/files")


def test_parley_resolver_rejects_reusing_the_agent_api_key():
    with pytest.raises(ValueError, match="distinta"):
        Settings(
            agent_api_key="shared-secret",
            parley_file_base_url="https://portal.example.com/api/files",
            parley_file_bearer_token="shared-secret",
            parley_file_capability_scope="agent-files",
        )


def test_parley_resolver_rejects_reusing_the_openai_api_key():
    with pytest.raises(ValueError, match="distinta"):
        Settings(
            openai_api_key="shared-secret",
            parley_file_base_url="https://portal.example.com/api/files",
            parley_file_bearer_token="shared-secret",
            parley_file_capability_scope="agent-files",
        )


def test_parley_resolver_requires_an_explicit_agent_file_capability_scope():
    with pytest.raises(ValueError, match="capability_scope"):
        Settings(
            parley_file_base_url="https://portal.example.com/api/files",
            parley_file_bearer_token="dedicated-secret",
        )


@pytest.mark.parametrize("value", [0, 10_485_761])
def test_parley_file_limit_is_bounded(value):
    with pytest.raises(ValueError, match="parley_file_max_bytes"):
        Settings(parley_file_max_bytes=value)


def test_request_body_limit_reads_environment(monkeypatch):
    monkeypatch.setenv("MAX_REQUEST_BODY_BYTES", "1048576")

    assert Settings.from_env().max_request_body_bytes == 1_048_576


@pytest.mark.parametrize("value", [65_535, 2_097_153])
def test_request_body_limit_is_bounded(value):
    with pytest.raises(ValueError, match="max_request_body_bytes"):
        Settings(max_request_body_bytes=value)
