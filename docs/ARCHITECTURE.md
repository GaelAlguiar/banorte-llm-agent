# Arquitectura

La solución separa transporte, política del agente, recuperación, conocimiento y modelo. FastAPI adapta el protocolo Open Responses; el agente selecciona una skill declarativa; el recuperador busca evidencia autorizada; OpenAI redacta la respuesta con instrucciones de grounding.

## Flujo

1. El cliente envía JSON y un Bearer token a `/v1/responses`.
2. La API valida tipo, tamaño y tasa.
3. Antes del RAG, el agente bloquea secretos inequívocos mediante un fast-path
   determinista. Si `token` o `prompt` tienen intención ambigua, un clasificador
   semántico recibe solo la pregunta y devuelve un enum estricto. Errores o
   salidas inválidas fallan cerrado y no acceden a recuperación.
4. El agente elige una skill determinista según la intención permitida.
5. La skill restringe las categorías y las fuentes exactas de conocimiento
   consultables; el mismo allowlist se aplica al intento principal y al fallback.
6. Azure AI Search combina BM25 y similitud vectorial, aplica filtros y un umbral.
7. El modelo recibe pregunta, reglas y fragmentos sanitizados.
8. La API devuelve JSON tipado o eventos SSE.

Tanto el endpoint Open Responses como la interfaz Flask delegan en la misma
instancia de `CvAgentService`. Los transportes validan su contrato, pero no
repiten decisiones de privacidad; por ello cada consulta se clasifica una sola
vez y tiene el mismo comportamiento antes de recuperar evidencia.

## Implementación productiva

Azure Container Apps consulta el índice con identidad administrada y el rol
`Search Index Data Reader`. La creación del esquema y la sincronización se
ejecutan fuera del proceso web. No existe fallback local en producción: la
sonda `/health/ready` informa si el índice no está disponible.

Para mayor escala se añadirían caché distribuida, APIM, OpenTelemetry, colas
para ingesta, versionado de índices y pruebas canary.
