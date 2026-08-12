# Interoperabilidad segura de adjuntos

## Contratos soportados

El agente acepta dos contratos sin mezclarlos:

1. Una URL HTTPS temporal bajo `input_image.image_url` o
   `input_file.file_url`. El host debe pertenecer a
   `ATTACHMENT_TRUSTED_HOSTS`.
2. Una referencia opaca `parley-file:file_<identificador>`. Sólo se habilita
   cuando existe una base fija y una credencial de lectura exclusiva para el
   almacenamiento del portal.

El segundo contrato es necesario porque el cliente observado representa todas
las cargas como `input_image`, incluso los PDF. El tipo real se obtiene de la
respuesta autenticada del resolver, no de la etiqueta enviada por el cliente.

## Flujo del resolver

```text
Referencia opaca
  -> validación estricta del identificador
  -> base HTTPS fija configurada por operación
  -> resolución DNS pública
  -> GET con bearer de lectura independiente
  -> sin redirecciones
  -> límite de bytes + MIME + firma del contenido
  -> clasificación imagen/documento
  -> Base64 temporal para OpenAI Responses
  -> descarte al finalizar la solicitud
```

No se aceptan rutas, queries o hosts desde el mensaje. Los errores del servicio
remoto se convierten en una respuesta genérica que no incluye el identificador,
la URL ni la credencial. Los bytes no se escriben en disco, logs, respuestas ni
la base de conocimiento.

## Condición operativa

Una referencia opaca no es por sí misma una autorización. Si el endpoint de
descarga requiere la sesión del usuario y el portal no entrega una credencial
de servicio, el agente no puede ni debe intentar reutilizar cookies o su propia
API key. En ese estado el resolver permanece deshabilitado y la solicitud falla
cerrada. La integración end-to-end se habilita únicamente cuando el operador
proporciona un bearer de lectura acotado o sustituye la referencia por una URL
HTTPS firmada y temporal.
