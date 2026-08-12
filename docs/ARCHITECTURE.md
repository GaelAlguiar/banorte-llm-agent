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
6. La ingesta conserva 17 fuentes autorizadas y genera chunks estables por
   encabezado para los documentos extensos; los pequeños permanecen completos.
7. Azure AI Search combina BM25 y similitud vectorial, aplica filtros por
   documento padre y categoría, umbral y diversidad entre padres/secciones.
8. El modelo recibe pregunta, reglas y los fragmentos localizados sanitizados.
9. La API devuelve JSON tipado o eventos SSE con trazabilidad pública segura.

Tanto el endpoint Open Responses como la interfaz Flask delegan en la misma
instancia de `CvAgentService`. Los transportes validan su contrato, pero no
repiten decisiones de privacidad; por ello cada consulta se clasifica una sola
vez y tiene el mismo comportamiento antes de recuperar evidencia.

Las ocho preguntas sugeridas son constantes controladas por la aplicación y se
preclasifican como benignas para evitar una llamada adicional. Cualquier otra
entrada, incluso una consulta profesional sobre Gael, pasa por el clasificador
semántico salvo que el fast-path detecte una solicitud sensible inequívoca.

## Implementación productiva

Azure Container Apps consulta el índice con identidad administrada y el rol
`Search Index Data Reader`. La creación del esquema y la sincronización se
ejecutan fuera del proceso web. No existe fallback local en producción: la
sonda `/health/ready` informa si el índice no está disponible.

`document_id` identifica una de las 17 fuentes; `chunk_id` es la clave estable
del fragmento indexado. Una sección que supera el límite se divide por párrafos
con solapamiento semántico acotado; el ID añade `part-NN`. Ningún adaptador
trunca silenciosamente el extracto después de recuperar. La sincronización
carga el conjunto de chunks vigente y
elimina IDs obsoletos, incluida la forma histórica de un registro por fuente.
La evidencia entregada al modelo conserva el extracto local de cada sección.
La respuesta externa omite `source_path`, URLs no públicas y scores numéricos;
las URLs requieren un dominio de evidencia explícitamente autorizado, sin DNS
en runtime. `metadata.evidence_ids` permanece como string de hasta 512
caracteres y la extensión superior `evidence` contiene el detalle seguro.

Para mayor escala se añadirían caché distribuida, APIM, OpenTelemetry, colas
para ingesta, versionado de índices y pruebas canary.
