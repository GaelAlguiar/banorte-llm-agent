# Seguridad

El endpoint usa una clave dedicada distinta de la clave del proveedor LLM. Los secretos se cargan en runtime y Azure Container Apps los referencia sin incorporarlos a la imagen.

El logger propio se configura explícitamente en nivel `INFO` al crear la
aplicación. Tanto FastAPI como Flask emiten los mismos eventos JSON allowlistados
en solicitudes exitosas y fallidas; la configuración no depende del nivel del
logger raíz ni añade handlers duplicados.

Controles implementados:

- autenticación Bearer con comparación en tiempo constante;
- máximo predeterminado de 1 MiB por cuerpo, configurable entre 64 KiB y 2 MiB,
  y 8,000 caracteres de entrada;
- máximo configurable de cuatro adjuntos, nombres de hasta 128 caracteres y
  allowlist de imágenes (PNG, JPEG, WebP, GIF) y documentos (PDF, texto,
  Markdown, DOCX), con validación de extensión y MIME cuando se declara;
- URLs de adjuntos exclusivamente HTTPS, sin credenciales ni puertos no
  estándar; se rechazan hosts codificados, single-label, sufijos internos y
  direcciones IPv4/IPv6 privadas, loopback, link-local, reservadas o multicast;
- validación sintáctica de FQDN sin resolución DNS durante la solicitud;
  rechaza también representaciones IP heredadas, enteras, octales, hexadecimales
  o mixtas, y exige una allowlist mediante `ATTACHMENT_TRUSTED_HOSTS`;
- `application/json` obligatorio;
- límite local de 30 solicitudes por minuto e IP;
- respuestas `Cache-Control: no-store` y request ID;
- guardrail previo a recuperación: las solicitudes inequívocas de secretos,
  inyección o recursos privados se bloquean de forma determinista;
- clasificación semántica con salida estructurada `sensitive|benign` para
  preguntas no inequívocas, incluidas las de tokens o prompts; recibe únicamente la pregunta,
  nunca evidencia del CV, y ante error, timeout o salida inválida falla cerrado
  sin consultar el índice;
- eventos operativos allowlistados emitidos por la ruta real del servicio: skill,
  `retrieval_hit_count`, `source_kind_mix` (sólo perfil, laboral o demostrativo),
  buckets de confianza, `attachment_count` y tipos de adjunto, `safety_decision`,
  `latency_ms`, estado y `error_type` acotado;
- logs sin prompts ni respuestas, URLs, IDs, rutas, nombres de archivo, chunks,
  tokens de autorización, datos de usuario ni secretos;
- errores del agente o proveedor convertidos a un 502 genérico sin propagar
  excepciones ni detalles del proveedor a ASGI/Uvicorn, al cuerpo o a los logs;
  el cuerpo usa `agent_execution_error` y la dimensión acotada usa
  `error_type: agent_error`, pues el límite cubre toda la ejecución del agente;
- solicitudes sensibles generadas con razonamiento `low`, aunque el cliente
  solicite `high`, para reservar un presupuesto visible a la negativa segura;
- imagen Linux ejecutada como usuario sin privilegios;
- skills YAML sin red, shell, URLs ni código ejecutable.

## Frontera de confianza de adjuntos

Para URLs HTTPS, OpenAI Responses recupera el adjunto remoto con `store: false`;
por ello la resolución DNS y el contenido final quedan dentro de la frontera de
confianza del proveedor. Para producción se recomienda configurar
`ATTACHMENT_TRUSTED_HOSTS` con los dominios exactos de la plataforma que emite
URLs firmadas y limitar su expiración. Cada entrada autoriza ese FQDN y sus
subdominios delimitados por punto; una lista vacía bloquea todos los adjuntos.
Ninguna URL, firma, nombre de archivo o
contenido se escribe en logs, respuestas, RAG ni almacenamiento de la aplicación.

Las referencias opacas `parley-file:` siguen otra frontera. Permanecen
deshabilitadas salvo que existan una base HTTPS fija y un bearer dedicado
distinto de `AGENT_API_KEY` y `OPENAI_API_KEY`. El identificador sólo admite caracteres
alfanuméricos minúsculos dentro de una longitud acotada. Antes de descargar, el
resolver selecciona una dirección pública validada y conecta directamente a
ella conservando el Host y SNI del FQDN fijo. Así la conexión autenticada no
vuelve a resolver el nombre entre la validación y el GET. No acepta redirecciones,
credenciales en URL, puertos alternativos ni destinos elegidos por el usuario.
Durante la descarga solicita codificación `identity`, rechaza contenido
comprimido y limita bytes declarados, reales y acumulados por solicitud,
valida MIME y firma de PNG, JPEG, GIF, WebP o PDF —o estructura básica
para texto— y conserva el contenido sólo en memoria durante la llamada. Las
referencias opacas no admiten DOCX porque un contenedor OOXML requiere
inspección antivirus y límites de descompresión adicionales.

Una solicitud sensible se clasifica sólo con su texto antes de recuperar la
referencia opaca y el adjunto ni siquiera
se reenvía al proveedor. Para una comparación permitida, el modelo recibe el
adjunto como dato temporal no confiable junto con evidencia autorizada acotada;
las instrucciones embebidas nunca sustituyen la política del sistema.

El middleware no confía en `Content-Length`: autentica y aplica el rate limit
antes de reservar el cuerpo, consume el flujo ASGI por chunks y detiene la
solicitud al superar `MAX_REQUEST_BODY_BYTES`. Sólo reproduce para el parser
JSON un cuerpo aceptado. Esto cubre transferencias fragmentadas o sin cabecera.

CI prueba fixtures PNG y PDF reales con un resolver HTTP falso: verifica bearer
separado, DNS, redirecciones, errores upstream, límites, MIME, firma binaria y
payload de OpenAI. No demuestra acceso al almacenamiento real del portal; ese
acceso depende de una credencial de lectura que su contrato actual no entrega.

La versión del reto no afirma cumplimiento bancario. En producción se agregarían APIM/WAF, Key Vault con identidad administrada, rate limiting distribuido, SIEM, escaneo de imágenes y dependencias, rotación de secretos, redes privadas y políticas formales de retención.

La clasificación semántica mejora la intención frente a listas extensas de
palabras, a cambio de una llamada adicional y algo de latencia únicamente en
consultas de doble uso. El modelo predeterminado es el mismo configurado para
generación; `OPENAI_PRIVACY_CLASSIFIER_MODEL` permite separarlo sin codificar
un modelo que pudiera no estar disponible.

La decisión se ejecuta únicamente en el servicio compartido. FastAPI y Flask
no mantienen listas de bloqueo independientes, evitando resultados distintos
entre el endpoint registrado y la interfaz de demostración.

El fast-path no declara benignas entradas arbitrarias: sólo bloquea patrones
sensibles inequívocos. La única excepción sin llamada semántica son las ocho
preguntas sugeridas exactas, definidas y controladas por la propia aplicación.
