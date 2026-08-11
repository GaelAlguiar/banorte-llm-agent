# Agente de CV — Gael Alguiar

Agente conversacional en español construido para el Reto IA Banorte. Permite explorar el perfil, experiencia, habilidades y proyectos de Gael mediante un endpoint compatible con Open Responses. La solución prioriza evidencia verificable, respuestas concisas y una operación segura.

## Qué demuestra

- Python y FastAPI con contrato `POST /v1/responses` y streaming SSE.
- RAG sobre una base profesional sanitizada, con recuperación vectorial local, BM25, Reciprocal Rank Fusion y umbral de relevancia.
- Skills declarativas y auditables para perfil, proyectos, arquitectura, ajuste a la vacante, aprendizaje y privacidad.
- Guardrails contra extracción de secretos e instrucciones internas.
- Análisis multimodal de imágenes y archivos temporales sin agregarlos al RAG.
- Autenticación Bearer, límites de cuerpo, tipo de contenido y 30 solicitudes por minuto.
- Evaluación offline reproducible con 40 preguntas en español.
- Contenedor no root preparado para Azure Container Apps.

## Arquitectura

```text
Plataforma Banorte
  -> HTTPS + Bearer token
  -> FastAPI /v1/responses
      -> guardrails y selección de skill
      -> retrieval híbrido
          -> feature hashing vectorial
          -> BM25
          -> RRF + reranking + threshold
      -> OpenAI Responses API
      -> respuesta Open Responses JSON o SSE
```

El modelo redacta; los hechos provienen de `knowledge/`. Las etiquetas `directa`, `relacionada` y `transferible` evitan presentar experiencia adyacente como experiencia comprobada.

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

El endpoint acepta hasta cuatro adjuntos en el último mensaje del usuario. Las
imágenes se envían como `input_image.image_url` y los documentos como
`input_file.file_url`; ambos enlaces deben usar HTTPS. Se recomiendan PNG, JPG
y WebP para imágenes, y PDF, TXT, Markdown o DOCX para documentos.

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

## Evaluación

```bash
python -m pytest tests/cv_agent -q
python -m cv_agent.evaluation.runner
```

La evaluación no llama a OpenAI. Mide Recall@5, MRR, groundedness, privacidad, estilo, routing de skills y latencia. Los umbrales mínimos son 90% de Recall@5, 100% de privacidad, 90% de estilo y 90% de routing.

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
- Los skills públicos son YAML declarativo: no ejecutan shell, red ni código remoto.
- La limitación en memoria es suficiente para el reto; con múltiples réplicas se sustituiría por APIM, Front Door o un almacén distribuido.

Consulta [Arquitectura](docs/ARCHITECTURE.md), [Seguridad](docs/SECURITY.md), [Evaluación](docs/EVALUATION.md), [contrato de plataforma](docs/BANORTE_PLATFORM_CONTRACT.md) y [guion de demostración](docs/DEMO.md).

## Decisiones y límites

La versión del reto usa un índice en memoria por su pequeño volumen, arranque simple y evaluación determinista. En producción se migraría a Azure AI Search o PostgreSQL con pgvector, se añadiría telemetría distribuida y evaluación con conversaciones reales anonimizadas. El agente no aprende automáticamente de cada conversación: mejorar conocimiento, prompts o modelos requiere un ciclo controlado de datos, evaluación, revisión y despliegue.
