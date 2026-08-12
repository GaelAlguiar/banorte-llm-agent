# Azure AI Search: diseño y operación

## Propósito

Azure AI Search es el recuperador productivo del agente. Combina coincidencia
léxica y similitud vectorial para localizar evidencia profesional autorizada,
sin convertir el modelo generativo en fuente de hechos. El recuperador local se
reserva para pruebas reproducibles; producción falla de forma visible si Azure
no está disponible y nunca cambia silenciosamente de backend.

## Modelo del índice

Cada registro representa un fragmento temático de uno de los documentos
revisados en `knowledge/`. El esquema conserva:

- identificadores estables de documento y fragmento;
- título, sección, contenido y categoría;
- tipo y nivel de evidencia;
- referencia pública opcional y hash del contenido;
- vector generado con `text-embedding-3-small`.

Los fragmentos extensos se dividen por secciones y párrafos con solapamiento
acotado. Así se evita truncar evidencia relevante y se mantienen citas
trazables incluso cuando cambia otra parte del mismo documento.

## Recuperación híbrida

La consulta genera un embedding y ejecuta en una sola operación:

1. búsqueda textual BM25 para términos precisos, nombres y tecnologías;
2. búsqueda vectorial para equivalencia semántica;
3. filtros derivados de la skill seleccionada;
4. calibración del ranking, umbral de relevancia y diversidad por fuente.

El adaptador convierte los resultados al modelo interno `RetrievalHit`. Los
scores detallados y las rutas internas no salen en la respuesta pública; sólo
se exponen identificadores, etiquetas profesionales, confianza aproximada y
URLs HTTPS previamente autorizadas.

## Ingesta controlada

La sincronización se ejecuta separada de la API:

```bash
python -m cv_agent.retrieval.ingest --knowledge knowledge
```

El proceso valida el esquema, calcula hashes y embeddings, actualiza los
fragmentos vigentes y elimina registros obsoletos. Los adjuntos de una
conversación son contexto temporal: no se incorporan al índice ni producen
aprendizaje automático.

## Seguridad

- La API consulta Search con identidad administrada y el rol mínimo
  `Search Index Data Reader`.
- La operación de ingesta usa permisos administrativos sólo durante la
  sincronización; esas credenciales no están disponibles para el proceso web.
- Secretos, prompts, documentos, vectores y encabezados de autorización no se
  escriben en logs.
- Las categorías y fuentes consultables se limitan mediante allowlists por
  skill.
- Las URLs públicas de evidencia también requieren una allowlist exacta.

## Disponibilidad y observabilidad

`/health` confirma que el proceso responde. `/health/ready` comprueba además la
configuración y el acceso real al índice. La telemetría conserva únicamente
dimensiones seguras, como skill, cantidad de resultados, mezcla de tipos de
fuente, decisión de seguridad, latencia y clase de error.

## Operación

Antes de promover una revisión se verifican:

- sincronización completa de los documentos autorizados;
- acceso de lectura mediante identidad administrada;
- disponibilidad de `/health/ready`;
- recuperación correcta para consultas representativas;
- rechazo de preguntas fuera de alcance y solicitudes sensibles;
- pruebas unitarias, contrato Open Responses y evaluación offline.

Para escalar la solución se puede añadir versionado de índices, despliegue
canary, caché distribuida, telemetría OpenTelemetry y una cola para ingestas.
Estas extensiones no cambian el límite principal: ninguna conversación modifica
la base profesional sin revisión y versionado explícitos.
