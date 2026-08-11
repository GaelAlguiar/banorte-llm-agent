#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="rg-prueba-b-gael-ai"
LOCATION="eastus"
ACR_NAME="acrpruebabgaelai"
ENVIRONMENT_NAME="cae-prueba-b-gael-ai"
APP_NAME="ca-prueba-b-gael-ai"
IMAGE_NAME="prueba-b-gael-ai"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"
: "${EXPECTED_SUBSCRIPTION:?Exporta EXPECTED_SUBSCRIPTION antes de desplegar.}"

command -v az >/dev/null || { echo "Azure CLI no está instalado." >&2; exit 1; }
command -v jq >/dev/null || { echo "jq no está instalado." >&2; exit 1; }
: "${OPENAI_API_KEY:?Exporta OPENAI_API_KEY antes de desplegar.}"
: "${AGENT_API_KEY:?Exporta AGENT_API_KEY antes de desplegar.}"

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
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

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
    --output none
  az containerapp update \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --image "$IMAGE" \
    --set-env-vars \
      OPENAI_API_KEY=secretref:openai-api-key \
      AGENT_API_KEY=secretref:agent-api-key \
      OPENAI_MODEL=gpt-5.6 \
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
    --ingress external \
    --target-port 8000 \
    --transport auto \
    --secrets openai-api-key="$OPENAI_API_KEY" agent-api-key="$AGENT_API_KEY" \
    --env-vars \
      OPENAI_API_KEY=secretref:openai-api-key \
      AGENT_API_KEY=secretref:agent-api-key \
      OPENAI_MODEL=gpt-5.6 \
      APP_ENV=production \
    --min-replicas 1 \
    --max-replicas 3 \
    --cpu 0.5 \
    --memory 1.0Gi \
    --output none
fi

probe_file="$(mktemp)"
trap 'rm -f "$probe_file"' EXIT
az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --output json \
  | jq '.properties.template.containers[0].probes = [
      {"type":"Liveness","httpGet":{"path":"/health","port":8000},"periodSeconds":30,"timeoutSeconds":5,"failureThreshold":3},
      {"type":"Readiness","httpGet":{"path":"/health","port":8000},"periodSeconds":10,"timeoutSeconds":5,"failureThreshold":3}
    ]' > "$probe_file"
az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --yaml "$probe_file" \
  --output none

fqdn="$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query properties.configuration.ingress.fqdn --output tsv)"
revision="$(az containerapp revision list --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query '[0].name' --output tsv)"
echo "Endpoint: https://$fqdn/v1"
echo "Revisión: $revision"
