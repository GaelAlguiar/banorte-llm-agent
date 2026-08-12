# Seguridad

El endpoint usa una clave dedicada distinta de la clave del proveedor LLM. Los secretos se cargan en runtime y Azure Container Apps los referencia sin incorporarlos a la imagen.

Controles implementados:

- autenticación Bearer con comparación en tiempo constante;
- máximo de 64 KiB por cuerpo y 8,000 caracteres de entrada;
- `application/json` obligatorio;
- límite local de 30 solicitudes por minuto e IP;
- respuestas `Cache-Control: no-store` y request ID;
- guardrail previo a recuperación: las solicitudes inequívocas de secretos,
  inyección o recursos privados se bloquean de forma determinista;
- clasificación semántica con salida estructurada `sensitive|benign` para
  preguntas no inequívocas, incluidas las de tokens o prompts; recibe únicamente la pregunta,
  nunca evidencia del CV, y ante error, timeout o salida inválida falla cerrado
  sin consultar el índice;
- logs allowlistados sin prompts, chunks, tokens de autorización ni secretos;
- imagen Linux ejecutada como usuario sin privilegios;
- skills YAML sin red, shell, URLs ni código ejecutable.

La versión del reto no afirma cumplimiento bancario. En producción se agregarían APIM/WAF, Key Vault con identidad administrada, rate limiting distribuido, SIEM, escaneo de imágenes y dependencias, rotación de secretos, redes privadas y políticas formales de retención.

La clasificación semántica mejora la intención frente a listas extensas de
palabras, a cambio de una llamada adicional y algo de latencia únicamente en
consultas de doble uso. El modelo predeterminado es el mismo configurado para
generación; `OPENAI_PRIVACY_CLASSIFIER_MODEL` permite separarlo sin codificar
un modelo que pudiera no estar disponible.

La decisión se ejecuta únicamente en el servicio compartido. FastAPI y Flask
no mantienen listas de bloqueo independientes, evitando resultados distintos
entre el endpoint registrado y la interfaz de demostración.
