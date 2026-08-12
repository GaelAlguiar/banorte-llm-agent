# Azure Container Apps

El despliegue crea recursos aislados de prueba en `eastus`: resource group,
Azure Container Registry Basic, Azure AI Search Free, Container Apps
Environment y una Container App con HTTPS público. Los nombres usan el prefijo
discreto `prueba-b`.

```bash
export OPENAI_API_KEY
export AGENT_API_KEY
export EXPECTED_SUBSCRIPTION
CONFIRM_AZURE_CONTEXT=YES bash infra/azure/deploy.sh
```

El despliegue conserva los adjuntos deshabilitados por omisión
(`MAX_ATTACHMENTS=0`). Para habilitarlos después de confirmar el dominio de
cargas de la plataforma, exporta un límite entre 1 y 4 y una allowlist de FQDN
públicos separada por comas:

```bash
export MAX_ATTACHMENTS=2
export ATTACHMENT_TRUSTED_HOSTS="<dominio-publico-de-cargas>"
CONFIRM_AZURE_CONTEXT=YES bash infra/azure/deploy.sh
```

No documentes aquí el valor operativo real si es privado. El script transmite
ambas variables tanto al crear como al actualizar la Container App y se detiene
antes de tocar Azure si se habilitan adjuntos sin hosts autorizados.

Si la plataforma entrega referencias opacas en lugar de URLs firmadas, utiliza
una credencial de lectura independiente. No reutilices `AGENT_API_KEY`:

```bash
export MAX_ATTACHMENTS=2
export PARLEY_FILE_BASE_URL="https://portal.example.com/ruta/api/files"
export PARLEY_FILE_BEARER_TOKEN
export PARLEY_FILE_MAX_BYTES=10485760
CONFIRM_AZURE_CONTEXT=YES bash infra/azure/deploy.sh
```

El token se registra como un secreto separado de Container Apps. Si falta la
base o el token, el despliegue se detiene; si ambos se omiten, elimina variables
antiguas del resolver y mantiene el flujo deshabilitado.

Antes de crear recursos, el script muestra tenant y suscripción y se detiene salvo que la confirmación sea explícita. Las claves se registran como secretos de Container Apps y la aplicación sólo recibe referencias. El endpoint público y la revisión se muestran al finalizar, pero las claves nunca se imprimen.

El script se detiene si la suscripción ya utiliza su servicio Search Free; no
cambia automáticamente a un SKU de pago. La clave administrativa de Search se
usa temporalmente para la ingesta y no se registra como secreto del servicio
web. Container Apps consulta el índice mediante identidad administrada y el
rol `Search Index Data Reader`.

Para producción bancaria se evaluarían red privada, APIM/WAF, Key Vault e identidad administrada para el proveedor del modelo, políticas de egreso, observabilidad centralizada y un almacén distribuido para límites de tasa.

Endpoint desplegado para la demostración: `https://ca-prueba-b-gael-ai.agreeablefield-a028190c.eastus.azurecontainerapps.io/v1`.
