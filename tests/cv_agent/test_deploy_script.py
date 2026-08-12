from pathlib import Path


SCRIPT = Path("infra/azure/deploy.sh")


def test_deploy_script_uses_explicit_isolated_resources() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    for value in (
        "rg-prueba-b-gael-ai",
        "eastus",
        "acrpruebabgaelai",
        "cae-prueba-b-gael-ai",
        "ca-prueba-b-gael-ai",
    ):
        assert value in text
    lowered = text.lower().replace(
        "http401withbearerchallenge",
        "",
    )
    assert "banorte" not in lowered
    assert "challenge" not in lowered
    assert "reto" not in lowered


def test_deploy_script_confirms_account_and_uses_secret_references() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "az account show" in text
    assert "CONFIRM_AZURE_CONTEXT" in text
    assert 'EXPECTED_SUBSCRIPTION:?' in text
    assert "Enerey-Prod" not in text
    assert 'active_subscription' in text
    assert "secretref:openai-api-key" in text
    assert "secretref:agent-api-key" in text
    assert "--target-port 8000" in text
    assert "--min-replicas 1" in text
    assert "--max-replicas 3" in text
    assert "--cpu 0.5" in text
    assert "--memory 1.0Gi" in text


def test_deploy_script_does_not_echo_secret_values() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "set -x" not in text
    assert "echo $OPENAI_API_KEY" not in text
    assert "echo $AGENT_API_KEY" not in text
    assert "printf $OPENAI_API_KEY" not in text


def test_deploy_script_provisions_only_free_search_with_rbac() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    for marker in (
        "Microsoft.Search",
        "az search service create",
        "--sku free",
        "--aad-auth-failure-mode http401WithBearerChallenge",
        "Search Index Data Reader",
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_INDEX",
        "AZURE_SEARCH_ADMIN_KEY",
        "/health/ready",
    ):
        assert marker in text
    search_creation = text.split(
        "az search service create", 1
    )[1].split("fi", 1)[0]
    assert "--sku basic" not in search_creation.lower()
    assert "azure-search-admin-key" not in text


def test_deploy_script_stops_if_another_free_search_exists() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "Microsoft.Search/searchServices" in text
    assert "existing_free_search" in text
    assert "exit 5" in text


def test_deploy_script_passes_attachment_policy_on_create_and_update() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert ': "${MAX_ATTACHMENTS:=0}"' in text
    assert "ATTACHMENT_TRUSTED_HOSTS" in text
    assert text.count('MAX_ATTACHMENTS="$MAX_ATTACHMENTS"') == 2
    assert text.count(
        'ATTACHMENT_TRUSTED_HOSTS="$ATTACHMENT_TRUSTED_HOSTS"'
    ) == 2
    assert ': "${MAX_REQUEST_BODY_BYTES:=1048576}"' in text
    assert text.count(
        'MAX_REQUEST_BODY_BYTES="$MAX_REQUEST_BODY_BYTES"'
    ) == 2


def test_deploy_script_fails_if_multimodal_enabled_without_trusted_hosts() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'if [[ "$MAX_ATTACHMENTS" -gt 0' in text
    assert '-z "$ATTACHMENT_TRUSTED_HOSTS"' in text
    assert "no habilites adjuntos sin hosts autorizados" in text.lower()


def test_deploy_script_wires_optional_resolver_with_a_separate_secret() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert ': "${PARLEY_FILE_BASE_URL:=}"' in text
    assert ': "${PARLEY_FILE_BEARER_TOKEN:=}"' in text
    assert ': "${PARLEY_FILE_MAX_BYTES:=10485760}"' in text
    assert "parley-file-token" in text
    assert "PARLEY_FILE_BEARER_TOKEN=secretref:parley-file-token" in text
    assert "PARLEY_FILE_BEARER_TOKEN=secretref:agent-api-key" not in text
    assert "resolver_secret_args" in text
    assert "resolver_env_args" in text
    assert "--remove-env-vars" in text


def test_deploy_script_requires_complete_resolver_configuration() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'bool_resolver_base=' in text
    assert 'bool_resolver_token=' in text
    assert '[[ "$bool_resolver_base" != "$bool_resolver_token" ]]' in text


def test_deploy_script_rejects_agent_key_reuse_and_removes_stale_secret() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert '"$PARLEY_FILE_BEARER_TOKEN" == "$AGENT_API_KEY"' in text
    assert "az containerapp secret remove" in text
    assert "--secret-names parley-file-token" in text
