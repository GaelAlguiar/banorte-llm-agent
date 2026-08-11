# Seguridad

El endpoint usa una clave dedicada distinta de la clave del proveedor LLM. Los secretos se cargan en runtime y Azure Container Apps los referencia sin incorporarlos a la imagen.

Controles implementados:

- autenticación Bearer con comparación en tiempo constante;
- máximo de 64 KiB por cuerpo y 8,000 caracteres de entrada;
- `application/json` obligatorio;
- límite local de 30 solicitudes por minuto e IP;
- respuestas `Cache-Control: no-store` y request ID;
- detección de solicitudes de credenciales, prompts y datos internos;
- logs allowlistados sin prompts, chunks, tokens de autorización ni secretos;
- imagen Linux ejecutada como usuario sin privilegios;
- skills YAML sin red, shell, URLs ni código ejecutable.

La versión del reto no afirma cumplimiento bancario. En producción se agregarían APIM/WAF, Key Vault con identidad administrada, rate limiting distribuido, SIEM, escaneo de imágenes y dependencias, rotación de secretos, redes privadas y políticas formales de retención.
