# Azure Container Apps

El despliegue crea recursos aislados de prueba en `eastus`: resource group, Azure Container Registry Basic, Container Apps Environment y una Container App con HTTPS público. Los nombres usan el prefijo discreto `prueba-b`.

```bash
export OPENAI_API_KEY
export AGENT_API_KEY
export EXPECTED_SUBSCRIPTION
CONFIRM_AZURE_CONTEXT=YES bash infra/azure/deploy.sh
```

Antes de crear recursos, el script muestra tenant y suscripción y se detiene salvo que la confirmación sea explícita. Las claves se registran como secretos de Container Apps y la aplicación sólo recibe referencias. El endpoint público y la revisión se muestran al finalizar, pero las claves nunca se imprimen.

Para producción bancaria se evaluarían red privada, APIM/WAF, Key Vault e identidad administrada para el proveedor del modelo, políticas de egreso, observabilidad centralizada y un almacén distribuido para límites de tasa.

Endpoint desplegado para la demostración: `https://ca-prueba-b-gael-ai.agreeablefield-a028190c.eastus.azurecontainerapps.io/v1`.
