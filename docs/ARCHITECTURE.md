# Arquitectura

La solución separa transporte, política del agente, recuperación, conocimiento y modelo. FastAPI adapta el protocolo Open Responses; el agente selecciona una skill declarativa; el recuperador busca evidencia autorizada; OpenAI redacta la respuesta con instrucciones de grounding.

## Flujo

1. El cliente envía JSON y un Bearer token a `/v1/responses`.
2. La API valida tipo, tamaño, tasa y posibles solicitudes sensibles.
3. El agente elige una skill determinista según la intención.
4. La skill restringe las categorías y las fuentes exactas de conocimiento
   consultables; el mismo allowlist se aplica al intento principal y al fallback.
5. Azure AI Search combina BM25 y similitud vectorial, aplica filtros y un umbral.
6. El modelo recibe pregunta, reglas y fragmentos sanitizados.
7. La API devuelve JSON tipado o eventos SSE.

## Implementación productiva

Azure Container Apps consulta el índice con identidad administrada y el rol
`Search Index Data Reader`. La creación del esquema y la sincronización se
ejecutan fuera del proceso web. No existe fallback local en producción: la
sonda `/health/ready` informa si el índice no está disponible.

Para mayor escala se añadirían caché distribuida, APIM, OpenTelemetry, colas
para ingesta, versionado de índices y pruebas canary.
