# Contrato observado de la plataforma Reto IA Banorte

Fecha de verificación: 11 de agosto de 2026.

La documentación visible del reto no define un esquema técnico completo. Para reducir incertidumbre se consultó al agente Guía y se verificó el comportamiento público de su endpoint de referencia.

## Comportamiento confirmado

- La plataforma registra una URL base terminada en `/v1`.
- El agente expone `POST /v1/responses`.
- La entrada admite texto, `input_image` con `image_url` e `input_file` con
  `file_url`, usando enlaces temporales HTTPS.
- Acepta `input` como texto y el campo `model`.
- Acepta `stream: false` y devuelve JSON con `object: response`, estado, output tipado, uso y error.
- Acepta `stream: true` y devuelve `text/event-stream`.
- El streaming utiliza eventos `response.created`, `response.in_progress`, `response.output_item.added`, `response.content_part.added`, `response.output_text.delta`, `response.output_text.done`, `response.content_part.done`, `response.output_item.done` y `response.completed`, seguido de `[DONE]`.
- La API key es opcional al registrar un agente; cada propietario decide si su endpoint la requiere.
- No se requieren endpoints adicionales a `POST /v1/responses`.

## Decisiones de compatibilidad

El agente de Gael soporta JSON y SSE. Su contrato acepta campos adicionales para mantener compatibilidad futura. La autenticación se configura fuera de la lógica del agente y utiliza bearer token cuando `AGENT_API_KEY` está definida.

Los adjuntos conservan las partes nativas de Open Responses. Antes de enviarlas
al proveedor, el agente valida HTTPS, host público sintáctico, puerto, tipo,
extensión, MIME opcional, nombre y cantidad. No acepta ejecutables, archivos
comprimidos ni tipos desconocidos. Las imágenes admitidas son PNG, JPEG, WebP y
GIF; los documentos son PDF, TXT, Markdown y DOCX. `MAX_ATTACHMENTS` reduce el
límite predeterminado de cuatro y `TRUSTED_ATTACHMENT_HOSTS` puede restringir
las URLs firmadas a dominios exactos conocidos.

No se asumen límites de timeout o payload como requisitos oficiales. Se establecen límites propios, documentados y configurables, y se validará el comportamiento final desde el chat oficial después del despliegue.

## Estado del registro y entrega

El equipo del reto habilitó la opción `Añadir un agente` y el endpoint quedó
registrado y probado desde el chat oficial. La plataforma confirmó que admite
JSON y streaming SSE, sin endpoints adicionales.

Por el momento no se solicita video, presentación ni documento adicional. La
demostración consiste en el agente registrado, el repositorio público y la
evidencia técnica indicada por la propia plataforma.
