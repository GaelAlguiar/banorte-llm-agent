# Interoperabilidad segura de adjuntos

## Contratos soportados

El agente acepta dos contratos sin mezclarlos:

1. Una URL HTTPS temporal bajo `input_image.image_url` o
   `input_file.file_url`. El host debe pertenecer a
   `ATTACHMENT_TRUSTED_HOSTS`.
2. Una referencia opaca `parley-file:file_<identificador>`. Sólo se habilita
   cuando existe una base fija y una credencial de lectura exclusiva para el
almacenamiento del portal.

El resolver opaco admite imágenes, PDF y texto. DOCX sólo se acepta por la ruta
HTTPS confiable del proveedor; no se descarga en el agente sin inspección OOXML,
antivirus y límites de descompresión.

El segundo contrato es necesario porque el cliente observado representa todas
las cargas como `input_image`, incluso los PDF. El tipo real se obtiene de la
respuesta autenticada del resolver, no de la etiqueta enviada por el cliente.

## Flujo del resolver

```text
Referencia opaca
  -> validación estricta del identificador
  -> base HTTPS fija configurada por operación
  -> resolución DNS pública y conexión fijada a la IP validada con Host/SNI
  -> GET con bearer de lectura independiente
  -> sin redirecciones
  -> límite de bytes + MIME + firma del contenido
  -> clasificación imagen/documento
  -> Base64 temporal para OpenAI Responses
  -> descarte al finalizar la solicitud
```

La conexión usa una IP validada sin resolver de nuevo el FQDN y conserva el Host
y SNI originales para verificar TLS. En producción se combina con controles de
red de salida. No se aceptan rutas, queries o hosts desde el mensaje. Los errores del servicio
remoto se convierten en una respuesta genérica que no incluye el identificador,
la URL ni la credencial. Los bytes no se escriben en disco, logs, respuestas ni
la base de conocimiento.

## Condición operativa

Una referencia opaca no es por sí misma una autorización. Si el endpoint de
descarga requiere la sesión del usuario y el portal no entrega una credencial
de servicio, el agente no puede ni debe intentar reutilizar cookies o su propia
API key. En ese estado el resolver permanece deshabilitado y la solicitud falla
cerrada. La integración end-to-end se habilita únicamente cuando el operador
proporciona una capacidad de lectura de alcance mínimo y confirma que cada
identificador sólo es utilizable por la solicitud autorizada, o sustituye la
referencia por una URL HTTPS firmada, temporal y ligada a un solo archivo. Un
bearer amplio que convierta cualquier identificador conocido en autorización no
cumple esta precondición y no debe configurarse.

La aplicación exige la confirmación explícita
`PARLEY_FILE_CAPABILITY_SCOPE=agent-files`. Esta bandera no convierte una clave
amplia en una capacidad segura: documenta una garantía que debe imponer el
servidor del portal y evita activar el adaptador por accidente.
