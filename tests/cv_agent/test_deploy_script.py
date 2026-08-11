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
    lowered = text.lower()
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
