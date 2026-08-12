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
