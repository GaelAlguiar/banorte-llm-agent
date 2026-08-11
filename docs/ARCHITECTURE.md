# Arquitectura

La solución separa transporte, política del agente, recuperación, conocimiento y modelo. FastAPI adapta el protocolo Open Responses; el agente selecciona una skill declarativa; el recuperador busca evidencia autorizada; OpenAI redacta la respuesta con instrucciones de grounding.

## Flujo

1. El cliente envía JSON y un Bearer token a `/v1/responses`.
2. La API valida tipo, tamaño, tasa y posibles solicitudes sensibles.
3. El agente elige una skill determinista según la intención.
4. La skill restringe las categorías de conocimiento consultables.
5. El retrieval combina similitud vectorial, BM25 y RRF, y aplica un umbral.
6. El modelo recibe pregunta, reglas y fragmentos sanitizados.
7. La API devuelve JSON tipado o eventos SSE.

## Evolución productiva

Para mayor escala: Azure AI Search o pgvector, caché distribuida, APIM, identidad administrada, OpenTelemetry, colas para ingesta, versionado de índices, pruebas canary y revisión humana de nuevas fuentes.
