# Agente de CV — Gael Alguiar

Agente conversacional en español construido para el Reto IA Banorte. Permite explorar el perfil, experiencia, habilidades y proyectos de Gael mediante un endpoint compatible con Open Responses. La solución prioriza evidencia verificable, respuestas concisas y una operación segura.

## Qué demuestra

- Python y FastAPI con contrato `POST /v1/responses` y streaming SSE.
- RAG sobre 17 documentos fuente sanitizados, divididos por encabezados en chunks temáticos estables para Azure AI Search, con embeddings de OpenAI, búsqueda híbrida, filtros y umbral de relevancia.
- Skills declarativas y auditables para perfil, proyectos, arquitectura, ajuste a la vacante, aprendizaje y privacidad.
- Guardrail semántico previo al RAG contra extracción de secretos e instrucciones internas.
- Análisis multimodal de imágenes y archivos temporales sin agregarlos al RAG.
- Autenticación Bearer, límites de cuerpo, tipo de contenido y 30 solicitudes por minuto.
- Evaluación offline reproducible con 125 preguntas en español.
- Contenedor no root preparado para Azure Container Apps.

## Arquitectura

```text
Plataforma Banorte
  -> HTTPS + Bearer token
  -> FastAPI /v1/responses
      -> guardrail de privacidad previo al RAG
          -> fast-path determinista para secretos inequívocos
          -> clasificación semántica para entradas no preclasificadas
      -> selección de skill
      -> Azure AI Search
          -> búsqueda textual BM25
          -> búsqueda vectorial con embeddings
          -> fusión híbrida + filtros + threshold
          -> fragmentos localizados y diversificados por documento padre
      -> OpenAI Responses API
      -> respuesta Open Responses JSON o SSE con evidencia pública segura
```

El modelo redacta; los hechos provienen de `knowledge/`. Las etiquetas `directa`, `relacionada` y `transferible` evitan presentar experiencia adyacente como experiencia comprobada.

Los 17 archivos de `knowledge/` son las fuentes autorizadas, no el conteo de
registros del índice. La cantidad actual se deriva con
`len(load_knowledge_chunks(Path("knowledge")))`: los archivos
pequeños permanecen completos y los extensos se separan por secciones Markdown.
Cada chunk conserva `document_id`, `chunk_id`, título, sección y metadatos del
padre. El número de chunks puede cambiar cuando se edita el contenido sin que
cambie el concepto de 17 documentos fuente.

Las respuestas incluyen `metadata.evidence_ids` como string compacto (máximo
512 caracteres) y una extensión superior `evidence` tanto en JSON como en el
evento final de SSE. Sólo contiene identificadores estables, etiquetas profesionales,
un rango de confianza y URLs HTTPS públicas autorizadas; nunca rutas locales,
URLs privadas ni scores internos precisos.

## Uso local

Requiere Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Configura en `.env` una clave de OpenAI y una clave dedicada para quien consuma el agente. Nunca reutilices la clave de OpenAI como clave pública del endpoint.

```bash
set -a
source .env
set +a
python -m uvicorn app:app --reload --port 8000
```

Salud:

```bash
curl http://127.0.0.1:8000/health
```

En el despliegue, `/health/ready` comprueba además el acceso efectivo al
índice de Azure AI Search.

Consulta no streaming:

```bash
curl http://127.0.0.1:8000/v1/responses \
  -H "Authorization: Bearer $AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gael-cv-agent","input":"¿Cómo diseñó Gael su agente RAG?","stream":false}'
```

Para SSE cambia `stream` a `true` y agrega `-N` a `curl`.

### Esfuerzo de razonamiento

La plataforma puede solicitar un nivel de razonamiento controlado. El agente
acepta únicamente `low`, `medium` o `high` y no reenvía parámetros arbitrarios
al proveedor. Para la demostración se utiliza una configuración equilibrada:

```json
{
  "reasoning": {
    "effort": "medium"
  }
}
```

Un esfuerzo mayor puede mejorar tareas complejas, pero también incrementa la
latencia y el consumo. `medium` mantiene respuestas consistentes sin aplicar el
costo de la configuración más alta a todas las preguntas.

### Imágenes y archivos

El endpoint acepta hasta cuatro adjuntos en el último mensaje del usuario (el
límite puede reducirse con `MAX_ATTACHMENTS`). Las
imágenes se envían como `input_image.image_url` y los documentos como
`input_file.file_url`; ambos enlaces deben usar HTTPS. Sólo se permiten PNG,
JPG/JPEG, WebP o GIF para imágenes, y PDF, TXT, Markdown o DOCX para documentos.
El nombre de archivo tiene un máximo de 128 caracteres. Si la plataforma usa
dominios fijos para sus URLs firmadas, debe configurar
`ATTACHMENT_TRUSTED_HOSTS` mediante una lista separada por comas. Sin esta
allowlist, las solicitudes con adjuntos se rechazan de forma segura. Cada host
autoriza el dominio exacto y sus subdominios, pero nunca una coincidencia parcial.

```json
{
  "model": "gael-cv-agent",
  "input": [{
    "role": "user",
    "content": [
      {"type": "input_text", "text": "Compara esta vacante con el perfil de Gael"},
      {"type": "input_file", "file_url": "https://ejemplo.com/vacante.pdf", "filename": "vacante.pdf"}
    ]
  }]
}
```

Los adjuntos son contexto temporal y no se descargan en el contenedor, no se
persisten y no se incorporan automáticamente a la base vectorial. Sus
instrucciones se consideran contenido no confiable para impedir prompt
injection; las afirmaciones sobre Gael siguen requiriendo evidencia autorizada.
La skill `attachment_analysis` hace una sola llamada generativa con el adjunto
y un paquete compacto de evidencia profesional permitido. Extrae requisitos y
los mapea como evidencia directa, experiencia relacionada o capacidad
transferible, además de señalar fortalezas, brechas honestas y un siguiente
paso de aprendizaje.

Las pruebas automatizadas incluyen fixtures PNG y PDF reales para verificar
su estructura con Pillow y pypdf, la construcción del payload multimodal y el comportamiento del proveedor
simulado sin gastar tokens. No realizan una recuperación real del archivo por
OpenAI: esa prueba end-to-end queda reservada para el despliegue final mediante
la carga de un adjunto desde la plataforma y un host explícitamente autorizado.

## Demostración de la solución

La plataforma no solicita un video ni una presentación adicional. Este
repositorio, el agente registrado y las conversaciones de prueba constituyen
la demostración funcional. Una revisión técnica puede seguir este recorrido:

1. Preguntar por una experiencia laboral para comprobar que la respuesta
   identifica proyecto, participación e impacto.
2. Solicitar la arquitectura del RAG para observar recuperación híbrida,
   selección de skills y generación basada en evidencia.
3. Adjuntar una vacante o imagen y pedir una comparación con experiencia
   directa, relacionada y transferible.
4. Solicitar credenciales o instrucciones internas para validar los
   guardrails de privacidad.
5. Ejecutar la evaluación y las pruebas automatizadas para comprobar que el
   comportamiento es reproducible.

### Decisiones de ingeniería

**Diseño.** La solución separa API, política del agente, skills, recuperación,
conocimiento y modelo. Esta división permite probar cada componente y cambiar
el proveedor LLM o el motor vectorial sin reescribir el contrato público.

**Integración.** Se eligió Open Responses porque permite que la plataforma
consuma el agente mediante `POST /v1/responses`, tanto en JSON como en SSE. Los
archivos se entregan mediante URLs HTTPS temporales y no se incorporan al RAG
sin un proceso explícito de revisión.

**Despliegue.** La aplicación se empaqueta en Docker como usuario sin
privilegios y se ejecuta en Azure Container Apps. Los secretos se inyectan en
runtime y la imagen no contiene claves ni archivos de entorno.

**Operación.** El servicio expone una sonda de salud, aplica autenticación,
límites de tamaño y tasa, y registra únicamente metadatos permitidos. La matriz
de evaluación cubre recuperación, groundedness, privacidad, estilo y routing.
La aplicación desplegada consulta Azure AI Search con identidad administrada;
la ingesta usa permisos administrativos solamente durante una operación
separada y controlada.

**Criterio técnico.** Producción utiliza Azure AI Search para demostrar una
arquitectura cloud operable y escalable. El recuperador determinista local se
conserva exclusivamente para pruebas rápidas, reproducibles y sin costo; no
existe fallback silencioso cuando Azure está configurado como backend.

### Ingesta autorizada

La base se sincroniza de manera explícita. El proceso calcula hashes y
embeddings, actualiza documentos vigentes y elimina registros que ya no estén
en `knowledge/`:

```bash
python -m cv_agent.retrieval.ingest --knowledge knowledge
```

La ingesta requiere temporalmente `AZURE_SEARCH_ADMIN_KEY`. Esa credencial no
se guarda en la imagen ni se entrega al proceso web.

## Evaluación

```bash
python -m pytest tests/cv_agent -q
python -m cv_agent.evaluation.runner
```

La evaluación no llama a OpenAI: el adaptador devuelve evidencia, no prosa generada. Mide Recall@8, precisión de evidencia@8, MRR, groundedness, privacidad, `evidence_term_coverage`, `impact_evidence_coverage`, routing de skills y latencia. Conserva umbrales mínimos por métrica y categoría. El tono y la afirmación de participación se validan con revisiones manuales del endpoint live.

## Evidencia pública complementaria

| Proyecto | Fuente pública | Alcance de la corroboración |
| --- | --- | --- |
| Enerey | [Sitio institucional](https://enereylatam.com/) | Existencia pública de la empresa. |
| Aplicación Enerey | [Ficha en App Store](https://apps.apple.com/mx/app/enerey/id6736633080) | Identifica la aplicación y muestra `© Gael Alguiar`; corrobora autoría pública, no cada componente técnico. |
| Global | [Sitio público](https://globalfls.com/) | Existencia del proyecto; la participación freelance fue confirmada por Gael. |
| Lugra | [Sitio público](https://www.lugramx.com/) | Existencia del proyecto; la participación freelance fue confirmada por Gael. |

Estas fuentes complementan el CV y la experiencia confirmada; no sustituyen la
evidencia laboral ni amplían el alcance técnico atribuido.

## Docker

```bash
docker build -t gael-cv-agent:local .
docker run --rm -p 8000:8000 \
  -e OPENAI_API_KEY \
  -e AGENT_API_KEY \
  gael-cv-agent:local
```

## Seguridad y operación

- Los secretos se inyectan por variables o secret references; no se guardan en Git.
- `/health` es público y no devuelve configuración.
- `/v1/responses` usa comparación constante del token.
- Los logs contienen metadatos allowlistados, no prompts, documentos ni headers.
- Las entradas no preclasificadas añaden una llamada breve que recibe solo la
  pregunta, usa razonamiento `none`, un enum JSON estricto y hasta 128 tokens de
  salida antes de recuperar evidencia. Una falla, timeout, respuesta incompleta
  o salida inválida se clasifica como sensible y no consulta el índice
  (fail closed).
- Los skills públicos son YAML declarativo: no ejecutan shell, red ni código remoto.
- La identidad de Container Apps recibe únicamente `Search Index Data Reader`.
- Con múltiples réplicas, el límite de tasa se movería a APIM, Front Door o un almacén distribuido.

Consulta [Arquitectura](docs/ARCHITECTURE.md), [Seguridad](docs/SECURITY.md), [Evaluación](docs/EVALUATION.md), [contrato de plataforma](docs/BANORTE_PLATFORM_CONTRACT.md) y [guion de demostración](docs/DEMO.md).

## Decisiones y límites

La versión desplegada usa Azure AI Search Free con búsqueda híbrida e identidad
administrada. La evaluación offline conserva un motor determinista para que CI
no dependa de red, credenciales ni consumo externo. El agente no aprende
automáticamente de cada conversación: mejorar conocimiento, prompts o modelos
requiere un ciclo controlado de datos, evaluación, revisión e ingesta.
