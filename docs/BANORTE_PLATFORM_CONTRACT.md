# Contrato observado de la plataforma Reto IA Banorte

Fecha de verificación: 12 de agosto de 2026.

La documentación visible del reto no define un esquema técnico completo. Para reducir incertidumbre se consultó al agente Guía y se verificó el comportamiento público de su endpoint de referencia.

## Comportamiento confirmado

- La plataforma registra una URL base terminada en `/v1`.
- El agente expone `POST /v1/responses`.
- La entrada admite texto y partes multimodales. El cliente carga primero el
  archivo a `POST /api/files` y después envía al agente una parte
  `input_image` cuyo `image_url` es `parley-file:file_<identificador>`, incluso
  cuando el archivo original es un PDF.
- Acepta `input` como texto y el campo `model`.
- Acepta `stream: false` y devuelve JSON con `object: response`, estado, output tipado, uso y error.
- Acepta `stream: true` y devuelve `text/event-stream`.
- El streaming utiliza eventos `response.created`, `response.in_progress`, `response.output_item.added`, `response.content_part.added`, `response.output_text.delta`, `response.output_text.done`, `response.content_part.done`, `response.output_item.done` y `response.completed`, seguido de `[DONE]`.
- La API key es opcional al registrar un agente; cada propietario decide si su endpoint la requiere.
- No se requieren endpoints adicionales a `POST /v1/responses`.

## Decisiones de compatibilidad

El agente de Gael soporta JSON y SSE. Su contrato acepta campos adicionales para mantener compatibilidad futura. La autenticación se configura fuera de la lógica del agente y utiliza bearer token cuando `AGENT_API_KEY` está definida.

`max_output_tokens` se aplica de igual forma en JSON y SSE. La API rechaza con
422 cualquier presupuesto inferior a 256; nunca aumenta el límite solicitado
por el cliente. Los valores superiores se acotan a 1,200 tokens antes de llegar
al proveedor. Si se omite, el servicio usa un presupuesto por intención: 256
para privacidad, 600 para perfil, 700 para respuestas conductuales, aprendizaje
y capacidades, y 900 para arquitectura, proyectos, ajuste al rol y adjuntos.
Estos límites mantienen respuestas profesionales suficientemente detalladas sin
permitir salidas accidentalmente extensas.

Si el medidor está habilitado, el texto termina con dos saltos de línea y un pie
como `1,234 tokens · 67.2% disponible`, compatible con clientes que ignoran
extensiones JSON. `usage` contiene los tokens reales de esa generación y
`budget.available_percent` replica el porcentaje sin revelar dinero.

El servicio es deliberadamente sin estado y llama al proveedor con `store: false`.
Por ello, `previous_response_id` no está soportado: un valor no nulo recibe un
error 400 `unsupported_previous_response_id`; `null` y la omisión conservan el
comportamiento normal. El campo nunca se ignora silenciosamente.

Los adjuntos HTTPS conservan las partes nativas de Open Responses. Antes de enviarlas
al proveedor, el agente valida HTTPS, host público sintáctico, puerto, tipo,
extensión, MIME opcional, nombre y cantidad. No acepta ejecutables, archivos
comprimidos ni tipos desconocidos. Las imágenes admitidas son PNG, JPEG, WebP y
GIF; los documentos son PDF, TXT, Markdown y DOCX. `MAX_ATTACHMENTS` reduce el
límite predeterminado de cuatro. `ATTACHMENT_TRUSTED_HOSTS` es obligatorio para
habilitar adjuntos y autoriza dominios conocidos exactos y sus subdominios.
Para la referencia opaca observada, el agente exige un resolver independiente:
`PARLEY_FILE_BASE_URL` y `PARLEY_FILE_BEARER_TOKEN`. La referencia sólo admite
el identificador alfanumérico esperado; no acepta rutas, queries, fragmentos ni
espacios. El resolver consulta una única base HTTPS, no sigue redirecciones,
fija la conexión a una IP pública validada con Host/SNI originales, limita el
total descargado por solicitud a 10 MiB y valida el tipo
de contenido antes de convertirlo en una entrada Base64 temporal para OpenAI.
Además requiere `PARLEY_FILE_CAPABILITY_SCOPE=agent-files`; sólo debe declararse
si el portal restringe la credencial a archivos asignados a este agente.

La descarga del portal requiere una sesión o credencial que no se reenvía al
endpoint del agente. La clave dedicada usada por la plataforma para invocar al
agente tampoco autoriza `GET /api/files/<identificador>`. Por ello la integración
real permanece deshabilitada y falla cerrada hasta que el operador proporcione
una credencial de lectura específica o emita una URL HTTPS firmada. CI verifica
el flujo completo con un transporte autenticado falso, sin afirmar acceso que
el contrato actual no concede.

El JSON de `POST /v1/responses` tiene un límite independiente y configurable de
1 MiB, acotado entre 64 KiB y 2 MiB. Es suficiente para el contrato por
referencia: el archivo de hasta 10 MiB se carga al portal y no viaja dentro del
JSON enviado al agente.

## Estado del registro y entrega

El equipo del reto habilitó la opción `Añadir un agente` y el endpoint quedó
registrado y probado desde el chat oficial. La plataforma confirmó que admite
JSON y streaming SSE, sin endpoints adicionales.

Por el momento no se solicita video, presentación ni documento adicional. La
demostración consiste en el agente registrado, el repositorio público y la
evidencia técnica indicada por la propia plataforma.
