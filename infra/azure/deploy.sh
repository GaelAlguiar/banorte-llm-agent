#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="rg-prueba-b-gael-ai"
LOCATION="eastus"
ACR_NAME="acrpruebabgaelai"
ENVIRONMENT_NAME="cae-prueba-b-gael-ai"
APP_NAME="ca-prueba-b-gael-ai"
IMAGE_NAME="prueba-b-gael-ai"
SEARCH_NAME="srch-prueba-b-gael-ai"
SEARCH_INDEX="cv-profile-v1"
: "${USAGE_STORAGE_ACCOUNT:=}"
: "${USAGE_STORAGE_TABLE:=agentusage}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
: "${EXPECTED_SUBSCRIPTION:?Exporta EXPECTED_SUBSCRIPTION antes de desplegar.}"

command -v az >/dev/null || { echo "Azure CLI no está instalado." >&2; exit 1; }
command -v jq >/dev/null || { echo "jq no está instalado." >&2; exit 1; }
: "${OPENAI_API_KEY:?Exporta OPENAI_API_KEY antes de desplegar.}"
: "${AGENT_API_KEY:?Exporta AGENT_API_KEY antes de desplegar.}"
: "${MAX_ATTACHMENTS:=0}"
: "${ATTACHMENT_TRUSTED_HOSTS:=}"
: "${MAX_REQUEST_BODY_BYTES:=1048576}"
: "${PARLEY_FILE_BASE_URL:=}"
: "${PARLEY_FILE_BEARER_TOKEN:=}"
: "${PARLEY_FILE_CAPABILITY_SCOPE:=}"
: "${PARLEY_FILE_MAX_BYTES:=10485760}"
: "${USAGE_METER_ENABLED:=false}"
if [[ "$USAGE_METER_ENABLED" == "true" ]]; then
  : "${USAGE_STORAGE_ACCOUNT:?Configura USAGE_STORAGE_ACCOUNT.}"
  : "${USAGE_TOTAL_BUDGET:?Configura USAGE_TOTAL_BUDGET.}"
  : "${USAGE_INITIAL_SPENT:?Configura USAGE_INITIAL_SPENT.}"
  : "${USAGE_INPUT_RATE:?Configura USAGE_INPUT_RATE.}"
  : "${USAGE_CACHED_INPUT_RATE:?Configura USAGE_CACHED_INPUT_RATE.}"
  : "${USAGE_OUTPUT_RATE:?Configura USAGE_OUTPUT_RATE.}"
fi
if ! [[ "$MAX_ATTACHMENTS" =~ ^[0-4]$ ]]; then
  echo "MAX_ATTACHMENTS debe ser un entero entre 0 y 4." >&2
  exit 6
fi
if [[ "$MAX_ATTACHMENTS" -gt 0 \
  && -z "$ATTACHMENT_TRUSTED_HOSTS" \
  && -z "$PARLEY_FILE_BASE_URL" ]]; then
  echo "No habilites adjuntos sin hosts autorizados en ATTACHMENT_TRUSTED_HOSTS." >&2
  exit 6
fi
if ! [[ "$MAX_REQUEST_BODY_BYTES" =~ ^[0-9]+$ ]] \
  || (( MAX_REQUEST_BODY_BYTES < 65536 || MAX_REQUEST_BODY_BYTES > 2097152 )); then
  echo "MAX_REQUEST_BODY_BYTES debe estar entre 65536 y 2097152." >&2
  exit 6
fi
if ! [[ "$PARLEY_FILE_MAX_BYTES" =~ ^[0-9]+$ ]] \
  || (( PARLEY_FILE_MAX_BYTES < 1 || PARLEY_FILE_MAX_BYTES > 10485760 )); then
  echo "PARLEY_FILE_MAX_BYTES debe estar entre 1 y 10485760." >&2
  exit 6
fi
bool_resolver_base=0
bool_resolver_token=0
[[ -n "$PARLEY_FILE_BASE_URL" ]] && bool_resolver_base=1
[[ -n "$PARLEY_FILE_BEARER_TOKEN" ]] && bool_resolver_token=1
if [[ "$bool_resolver_base" != "$bool_resolver_token" ]]; then
  echo "Configura juntos PARLEY_FILE_BASE_URL y PARLEY_FILE_BEARER_TOKEN." >&2
  exit 6
fi
if [[ "$bool_resolver_base" == "1" \
  && "$PARLEY_FILE_CAPABILITY_SCOPE" != "agent-files" ]]; then
  echo "Confirma PARLEY_FILE_CAPABILITY_SCOPE=agent-files sólo para una capacidad acotada." >&2
  exit 6
fi
if [[ "$bool_resolver_base" == "0" && -n "$PARLEY_FILE_CAPABILITY_SCOPE" ]]; then
  echo "PARLEY_FILE_CAPABILITY_SCOPE requiere un resolver configurado." >&2
  exit 6
fi
if [[ -n "$PARLEY_FILE_BEARER_TOKEN" \
  && ( "$PARLEY_FILE_BEARER_TOKEN" == "$AGENT_API_KEY" \
    || "$PARLEY_FILE_BEARER_TOKEN" == "$OPENAI_API_KEY" ) ]]; then
  echo "La credencial de archivos debe ser distinta de las demás claves." >&2
  exit 6
fi
resolver_secret_args=()
resolver_env_args=()
if [[ "$bool_resolver_base" == "1" ]]; then
  resolver_secret_args+=(parley-file-token="$PARLEY_FILE_BEARER_TOKEN")
  resolver_env_args+=(
    PARLEY_FILE_BASE_URL="$PARLEY_FILE_BASE_URL"
    PARLEY_FILE_BEARER_TOKEN=secretref:parley-file-token
    PARLEY_FILE_CAPABILITY_SCOPE="$PARLEY_FILE_CAPABILITY_SCOPE"
    PARLEY_FILE_MAX_BYTES="$PARLEY_FILE_MAX_BYTES"
  )
fi

echo "Contexto de Azure que recibirá los recursos:"
az account show --query '{subscription:name,state:state}' --output table
active_subscription="$(az account show --query name --output tsv)"
if [[ "$active_subscription" != "$EXPECTED_SUBSCRIPTION" ]]; then
  echo "La suscripción activa no coincide con la autorizada." >&2
  exit 4
fi
if [[ "${CONFIRM_AZURE_CONTEXT:-}" != "YES" ]]; then
  echo "Detenido. Repite con CONFIRM_AZURE_CONTEXT=YES tras validar el contexto." >&2
  exit 2
fi

az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait
az provider register --namespace Microsoft.Search --wait
az provider register --namespace Microsoft.Storage --wait
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

usage_secret_args=()
usage_env_args=(USAGE_METER_ENABLED="$USAGE_METER_ENABLED")
if [[ "$USAGE_METER_ENABLED" == "true" ]]; then
  if ! az storage account show --name "$USAGE_STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
    az storage account create --name "$USAGE_STORAGE_ACCOUNT" \
      --resource-group "$RESOURCE_GROUP" --location "$LOCATION" \
      --sku Standard_LRS --kind StorageV2 --output none
  fi
  az resource create \
    --resource-group "$RESOURCE_GROUP" \
    --resource-type Microsoft.Storage/storageAccounts/tableServices/tables \
    --name "$USAGE_STORAGE_ACCOUNT/default/$USAGE_STORAGE_TABLE" \
    --api-version 2023-01-01 \
    --properties '{}' \
    --output none
  usage_secret_args+=(
    usage-total-budget="$USAGE_TOTAL_BUDGET"
    usage-initial-spent="$USAGE_INITIAL_SPENT"
    usage-input-rate="$USAGE_INPUT_RATE"
    usage-cached-input-rate="$USAGE_CACHED_INPUT_RATE"
    usage-output-rate="$USAGE_OUTPUT_RATE"
  )
  usage_env_args+=(
    USAGE_STORAGE_ACCOUNT="$USAGE_STORAGE_ACCOUNT"
    USAGE_STORAGE_TABLE="$USAGE_STORAGE_TABLE"
    USAGE_TOTAL_BUDGET=secretref:usage-total-budget
    USAGE_INITIAL_SPENT=secretref:usage-initial-spent
    USAGE_INPUT_RATE=secretref:usage-input-rate
    USAGE_CACHED_INPUT_RATE=secretref:usage-cached-input-rate
    USAGE_OUTPUT_RATE=secretref:usage-output-rate
  )
fi

if ! az search service show --name "$SEARCH_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  existing_free_search="$(az resource list \
    --resource-type Microsoft.Search/searchServices \
    --query "[?sku.name=='free'].name | [0]" \
    --output tsv)"
  if [[ -n "$existing_free_search" ]]; then
    echo "Ya existe un servicio Azure AI Search Free en la suscripción; no se creará un SKU de pago." >&2
    exit 5
  fi
  az search service create \
    --name "$SEARCH_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --sku free \
    --auth-options aadOrApiKey \
    --aad-auth-failure-mode http401WithBearerChallenge \
    --semantic-search free \
    --output none
fi

AZURE_SEARCH_ENDPOINT="https://$SEARCH_NAME.search.windows.net"
AZURE_SEARCH_INDEX="$SEARCH_INDEX"
AZURE_SEARCH_ADMIN_KEY="$(az search admin-key show \
  --service-name "$SEARCH_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query primaryKey \
  --output tsv)"
export AZURE_SEARCH_ENDPOINT AZURE_SEARCH_INDEX AZURE_SEARCH_ADMIN_KEY
python3 -m cv_agent.retrieval.ingest --knowledge knowledge
unset AZURE_SEARCH_ADMIN_KEY

if ! az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  availability="$(az acr check-name --name "$ACR_NAME" --query nameAvailable --output tsv)"
  [[ "$availability" == "true" ]] || {
    echo "El nombre global de ACR no está disponible; define otro nombre seguro en el script." >&2
    exit 3
  }
  az acr create \
    --name "$ACR_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --sku Basic \
    --admin-enabled false \
    --output none
fi

az acr build \
  --registry "$ACR_NAME" \
  --image "$IMAGE_NAME:$IMAGE_TAG" \
  . \
  --output none

if ! az containerapp env show --name "$ENVIRONMENT_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az containerapp env create \
    --name "$ENVIRONMENT_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none
fi

IMAGE="$ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG"
if az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  az containerapp secret set \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --secrets openai-api-key="$OPENAI_API_KEY" agent-api-key="$AGENT_API_KEY" \
      "${resolver_secret_args[@]}" "${usage_secret_args[@]}" \
    --output none
  if [[ "$bool_resolver_base" == "0" ]]; then
    az containerapp update \
      --name "$APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --remove-env-vars \
        PARLEY_FILE_BASE_URL \
        PARLEY_FILE_BEARER_TOKEN \
        PARLEY_FILE_CAPABILITY_SCOPE \
        PARLEY_FILE_MAX_BYTES \
      --output none
    stale_resolver_secret="$(az containerapp secret list \
      --name "$APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --query "[?name=='parley-file-token'].name | [0]" \
      --output tsv)"
    if [[ -n "$stale_resolver_secret" ]]; then
      az containerapp secret remove \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --secret-names parley-file-token \
        --output none
    fi
  fi
  if [[ "$USAGE_METER_ENABLED" != "true" ]]; then
    az containerapp update \
      --name "$APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --remove-env-vars \
        USAGE_STORAGE_ACCOUNT \
        USAGE_STORAGE_TABLE \
        USAGE_TOTAL_BUDGET \
        USAGE_INITIAL_SPENT \
        USAGE_INPUT_RATE \
        USAGE_CACHED_INPUT_RATE \
        USAGE_OUTPUT_RATE \
      --output none
    stale_usage_secrets="$(az containerapp secret list \
      --name "$APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --query "[?starts_with(name, 'usage-')].name" \
      --output tsv)"
    if [[ -n "$stale_usage_secrets" ]]; then
      stale_usage_secret_names=()
      while IFS= read -r stale_usage_secret; do
        [[ -n "$stale_usage_secret" ]] \
          && stale_usage_secret_names+=("$stale_usage_secret")
      done <<< "$stale_usage_secrets"
      az containerapp secret remove \
        --name "$APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --secret-names "${stale_usage_secret_names[@]}" \
        --output none
    fi
  fi
  az containerapp update \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --image "$IMAGE" \
    --set-env-vars \
      OPENAI_API_KEY=secretref:openai-api-key \
      AGENT_API_KEY=secretref:agent-api-key \
      OPENAI_MODEL=gpt-5.6 \
      EMBEDDING_MODEL=text-embedding-3-small \
      EMBEDDING_DIMENSIONS=1536 \
      AZURE_SEARCH_ENDPOINT="$AZURE_SEARCH_ENDPOINT" \
      AZURE_SEARCH_INDEX="$AZURE_SEARCH_INDEX" \
      AZURE_SEARCH_MIN_SCORE=0.03 \
      MAX_ATTACHMENTS="$MAX_ATTACHMENTS" \
      ATTACHMENT_TRUSTED_HOSTS="$ATTACHMENT_TRUSTED_HOSTS" \
      MAX_REQUEST_BODY_BYTES="$MAX_REQUEST_BODY_BYTES" \
      "${resolver_env_args[@]}" \
      "${usage_env_args[@]}" \
      APP_ENV=production \
    --min-replicas 1 \
    --max-replicas 3 \
    --cpu 0.5 \
    --memory 1.0Gi \
    --output none
else
  az containerapp create \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$ENVIRONMENT_NAME" \
    --image "$IMAGE" \
    --registry-server "$ACR_NAME.azurecr.io" \
    --registry-identity system \
    --system-assigned \
    --ingress internal \
    --target-port 8000 \
    --transport auto \
    --secrets openai-api-key="$OPENAI_API_KEY" agent-api-key="$AGENT_API_KEY" \
      "${resolver_secret_args[@]}" "${usage_secret_args[@]}" \
    --env-vars \
      OPENAI_API_KEY=secretref:openai-api-key \
      AGENT_API_KEY=secretref:agent-api-key \
      OPENAI_MODEL=gpt-5.6 \
      EMBEDDING_MODEL=text-embedding-3-small \
      EMBEDDING_DIMENSIONS=1536 \
      AZURE_SEARCH_ENDPOINT="$AZURE_SEARCH_ENDPOINT" \
      AZURE_SEARCH_INDEX="$AZURE_SEARCH_INDEX" \
      AZURE_SEARCH_MIN_SCORE=0.03 \
      MAX_ATTACHMENTS="$MAX_ATTACHMENTS" \
      ATTACHMENT_TRUSTED_HOSTS="$ATTACHMENT_TRUSTED_HOSTS" \
      MAX_REQUEST_BODY_BYTES="$MAX_REQUEST_BODY_BYTES" \
      "${resolver_env_args[@]}" \
      "${usage_env_args[@]}" \
      APP_ENV=production \
    --min-replicas 1 \
    --max-replicas 3 \
    --cpu 0.5 \
    --memory 1.0Gi \
    --output none
fi

az containerapp identity assign \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --system-assigned \
  --output none
principal_id="$(az containerapp identity show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query principalId \
  --output tsv)"
search_scope="$(az search service show \
  --name "$SEARCH_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query id \
  --output tsv)"
if ! az role assignment list \
  --assignee-object-id "$principal_id" \
  --scope "$search_scope" \
  --role "Search Index Data Reader" \
  --query '[0].id' \
  --output tsv | grep -q .; then
  az role assignment create \
    --assignee-object-id "$principal_id" \
    --assignee-principal-type ServicePrincipal \
    --role "Search Index Data Reader" \
    --scope "$search_scope" \
    --output none
fi
if [[ "$USAGE_METER_ENABLED" == "true" ]]; then
  storage_scope="$(az storage account show --name "$USAGE_STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" --query id --output tsv)"
  if ! az role assignment list --assignee-object-id "$principal_id" \
    --scope "$storage_scope" --role "Storage Table Data Contributor" \
    --query '[0].id' --output tsv | grep -q .; then
    az role assignment create --assignee-object-id "$principal_id" \
      --assignee-principal-type ServicePrincipal \
      --role "Storage Table Data Contributor" --scope "$storage_scope" \
      --output none
  fi
fi

probe_file="$(mktemp)"
trap 'rm -f "$probe_file"' EXIT
az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --output json \
  | jq '.properties.template.containers[0].probes = [
      {"type":"Liveness","httpGet":{"path":"/health","port":8000},"periodSeconds":30,"timeoutSeconds":5,"failureThreshold":3},
      {"type":"Readiness","httpGet":{"path":"/health/ready","port":8000},"periodSeconds":10,"timeoutSeconds":5,"failureThreshold":6}
    ]' > "$probe_file"
az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --yaml "$probe_file" \
  --output none

az containerapp ingress enable \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --type external \
  --target-port 8000 \
  --transport auto \
  --output none

fqdn="$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query properties.configuration.ingress.fqdn --output tsv)"
ready=0
for _ in $(seq 1 30); do
  if curl --fail --silent --show-error \
    "https://$fqdn/health/ready" >/dev/null; then
    ready=1
    break
  fi
  sleep 10
done
if [[ "$ready" != "1" ]]; then
  echo "La revisión no alcanzó readiness con sus dependencias." >&2
  exit 7
fi
revision="$(az containerapp revision list --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query '[0].name' --output tsv)"
echo "Endpoint: https://$fqdn/v1"
echo "Revisión: $revision"
