# Azure AI Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ejecutar el RAG desplegado sobre Azure AI Search con búsqueda híbrida, embeddings de OpenAI, ingesta controlada e identidad administrada.

**Architecture:** La API seleccionará un adaptador local en desarrollo y un adaptador Azure obligatorio en producción. Un comando de ingesta separado administrará el esquema y sincronizará los documentos; la aplicación web solo tendrá permisos de lectura mediante identidad administrada.

**Tech Stack:** Python 3.12, FastAPI, OpenAI embeddings, Azure AI Search, `azure-search-documents`, `azure-identity`, Azure Container Apps, pytest y Azure CLI.

---

## Estructura de archivos

- `cv_agent/retrieval/base.py`: contrato compartido por los motores de recuperación.
- `cv_agent/retrieval/azure_search.py`: consultas híbridas y conversión a `RetrievalHit`.
- `cv_agent/retrieval/embeddings.py`: proveedor de embeddings de OpenAI.
- `cv_agent/retrieval/factory.py`: selección explícita del backend por ambiente.
- `cv_agent/retrieval/ingest.py`: esquema y sincronización del índice.
- `cv_agent/config.py`: configuración validada de Azure Search.
- `cv_agent/main.py`: composición de dependencias y sonda de disponibilidad.
- `infra/azure/deploy.sh`: aprovisionamiento Free, RBAC, ingesta y despliegue.
- `tests/cv_agent/test_azure_search.py`: contrato de consulta de Azure.
- `tests/cv_agent/test_retrieval_factory.py`: selección de backend.
- `tests/cv_agent/test_ingest.py`: sincronización determinista.
- `tests/cv_agent/test_health.py`: disponibilidad de la dependencia.
- `tests/cv_agent/test_deploy_script.py`: controles de infraestructura y costo.

### Task 1: Dependencias y configuración

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`
- Modify: `cv_agent/config.py`
- Test: `tests/cv_agent/test_config.py`

- [ ] **Step 1: Escribir pruebas fallidas de configuración**

```python
from cv_agent.config import Settings


def test_production_requires_azure_search_configuration(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AZURE_SEARCH_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_SEARCH_INDEX", raising=False)

    settings = Settings.from_env()

    assert settings.azure_search_endpoint is None
    assert settings.azure_search_index == "cv-profile-v1"


def test_settings_read_azure_search_values(monkeypatch):
    monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://search.example.net")
    monkeypatch.setenv("AZURE_SEARCH_INDEX", "profile-test")
    monkeypatch.setenv("AZURE_SEARCH_MIN_SCORE", "0.03")

    settings = Settings.from_env()

    assert settings.azure_search_endpoint == "https://search.example.net"
    assert settings.azure_search_index == "profile-test"
    assert settings.azure_search_min_score == 0.03
```

- [ ] **Step 2: Verificar el estado rojo**

Run: `python -m pytest tests/cv_agent/test_config.py -q`

Expected: FAIL porque los campos de Azure todavía no existen.

- [ ] **Step 3: Añadir configuración mínima**

Agregar a `Settings`:

```python
azure_search_endpoint: str | None = None
azure_search_index: str = "cv-profile-v1"
azure_search_min_score: float = 0.03
embedding_dimensions: int = 1536
```

Leer `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_INDEX`,
`AZURE_SEARCH_MIN_SCORE` y `EMBEDDING_DIMENSIONS` en `from_env`. Documentar esos
nombres vacíos o con valores no secretos en `.env.example`.

Agregar a `requirements.txt`:

```text
azure-identity>=1.19,<2
azure-search-documents>=11.6,<12
```

- [ ] **Step 4: Ejecutar las pruebas de configuración**

Run: `python -m pytest tests/cv_agent/test_config.py tests/cv_agent/test_container_contract.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.example cv_agent/config.py tests/cv_agent/test_config.py
git commit -m "Configure Azure AI Search"
```

### Task 2: Contrato de recuperación y embeddings reales

**Files:**
- Create: `cv_agent/retrieval/base.py`
- Modify: `cv_agent/retrieval/embeddings.py`
- Modify: `cv_agent/retrieval/service.py`
- Modify: `cv_agent/agent/tools.py`
- Modify: `cv_agent/agent/service.py`
- Test: `tests/cv_agent/test_embeddings.py`

- [ ] **Step 1: Escribir pruebas fallidas del proveedor OpenAI**

```python
import numpy as np

from cv_agent.retrieval.embeddings import OpenAIEmbeddingProvider


def test_openai_embedding_provider_requests_configured_model():
    provider = OpenAIEmbeddingProvider("test-key", "text-embedding-3-small", 3)
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        item = type("Item", (), {"embedding": [0.1, 0.2, 0.3]})()
        return type("Response", (), {"data": [item]})()

    provider.client.embeddings.create = create

    result = provider.embed("experiencia con Azure")

    assert np.allclose(result, [0.1, 0.2, 0.3])
    assert captured == {
        "model": "text-embedding-3-small",
        "input": "experiencia con Azure",
        "dimensions": 3,
    }
```

- [ ] **Step 2: Verificar el estado rojo**

Run: `python -m pytest tests/cv_agent/test_embeddings.py -q`

Expected: FAIL porque `OpenAIEmbeddingProvider` no existe.

- [ ] **Step 3: Crear el contrato y proveedor mínimo**

Definir en `base.py`:

```python
from typing import Protocol

from cv_agent.knowledge.models import KnowledgeDocument
from cv_agent.retrieval.models import RetrievalHit


class RetrievalService(Protocol):
    documents: list[KnowledgeDocument]

    def search(
        self,
        query: str,
        top_k: int = 5,
        categories: set[str] | None = None,
    ) -> list[RetrievalHit]: ...

    def ready(self) -> bool: ...
```

Implementar `OpenAIEmbeddingProvider` con `OpenAI(..., timeout=30)` y hacer que
`HybridCvRetrieval.ready()` devuelva `True`. Cambiar las anotaciones de
`ProfileTools` y `CvAgentService` a `RetrievalService`.

- [ ] **Step 4: Ejecutar pruebas de embeddings y retrieval local**

Run: `python -m pytest tests/cv_agent/test_embeddings.py tests/cv_agent/test_retrieval.py tests/cv_agent/test_agent_policy.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add cv_agent/retrieval cv_agent/agent tests/cv_agent/test_embeddings.py
git commit -m "Add retrieval service contract"
```

### Task 3: Adaptador híbrido de Azure AI Search

**Files:**
- Create: `cv_agent/retrieval/azure_search.py`
- Test: `tests/cv_agent/test_azure_search.py`

- [ ] **Step 1: Escribir pruebas fallidas de consulta y mapeo**

```python
from cv_agent.retrieval.azure_search import AzureSearchRetrieval


class FakeEmbeddings:
    def embed(self, text):
        return [0.1, 0.2, 0.3]


class FakeSearchClient:
    def __init__(self):
        self.kwargs = None

    def search(self, **kwargs):
        self.kwargs = kwargs
        return [{
            "id": "terraform-banregio",
            "title": "Terraform en Banregio",
            "category": "infraestructura",
            "evidence_level": "directa",
            "impact_type": "confirmado",
            "source_kind": "laboral",
            "source": "experiencia profesional",
            "content": "Infraestructura modular con Terraform.",
            "@search.score": 0.91,
        }]


def test_search_sends_text_vector_and_category_filter():
    client = FakeSearchClient()
    retrieval = AzureSearchRetrieval(
        documents=[], client=client, embeddings=FakeEmbeddings(),
        min_score=0.03,
    )

    hits = retrieval.search(
        "experiencia con Terraform", top_k=3,
        categories={"infraestructura"},
    )

    assert hits[0].document_id == "terraform-banregio"
    assert client.kwargs["search_text"] == "experiencia con Terraform"
    assert client.kwargs["top"] == 3
    assert client.kwargs["filter"] == "category eq 'infraestructura'"
    assert client.kwargs["vector_queries"][0].fields == "content_vector"
```

Agregar pruebas separadas para escapar comillas en filtros, limitar `top_k` a
ocho, descartar puntajes inferiores al umbral y `ready()` con una consulta de
un resultado.

- [ ] **Step 2: Verificar el estado rojo**

Run: `python -m pytest tests/cv_agent/test_azure_search.py -q`

Expected: FAIL porque el adaptador no existe.

- [ ] **Step 3: Implementar la consulta híbrida mínima**

Crear `AzureSearchRetrieval` con `SearchClient`, un `EmbeddingProvider`, los
documentos cargados localmente solo para `get_project`, y `min_score`. Usar
`VectorizedQuery(vector=list(vector), k_nearest_neighbors=max(top_k, 5),
fields="content_vector")` junto con `search_text=query`. Mapear
`@search.score` a `score`, `vector_score` y `rrf_score`; usar `0.0` para el
puntaje léxico porque Azure devuelve el puntaje híbrido combinado.

- [ ] **Step 4: Ejecutar pruebas del adaptador**

Run: `python -m pytest tests/cv_agent/test_azure_search.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add cv_agent/retrieval/azure_search.py tests/cv_agent/test_azure_search.py
git commit -m "Add Azure AI Search retrieval"
```

### Task 4: Fábrica de backend y disponibilidad

**Files:**
- Create: `cv_agent/retrieval/factory.py`
- Modify: `cv_agent/main.py`
- Test: `tests/cv_agent/test_retrieval_factory.py`
- Test: `tests/cv_agent/test_health.py`

- [ ] **Step 1: Escribir pruebas fallidas de selección estricta**

```python
from pathlib import Path

import pytest

from cv_agent.config import Settings
from cv_agent.retrieval.factory import build_retrieval
from cv_agent.retrieval.service import HybridCvRetrieval


def test_local_environment_uses_local_retrieval():
    result = build_retrieval(
        Settings(environment="local"), Path("knowledge")
    )
    assert isinstance(result, HybridCvRetrieval)


def test_production_rejects_missing_search_endpoint():
    with pytest.raises(RuntimeError, match="AZURE_SEARCH_ENDPOINT"):
        build_retrieval(
            Settings(openai_api_key="key", environment="production"),
            Path("knowledge"),
        )
```

Agregar a `test_health.py` un agente falso cuyo retrieval implemente
`ready()`. Esperar `200 {"status":"ready",...}` cuando devuelve `True` y 503
cuando devuelve `False`.

- [ ] **Step 2: Verificar el estado rojo**

Run: `python -m pytest tests/cv_agent/test_retrieval_factory.py tests/cv_agent/test_health.py -q`

Expected: FAIL porque la fábrica y `/health/ready` no existen.

- [ ] **Step 3: Implementar fábrica y sonda**

`build_retrieval` debe construir `HybridCvRetrieval` salvo cuando
`environment == "production"`. En producción debe exigir endpoint, clave de
OpenAI e índice; crear `DefaultAzureCredential`, `SearchClient` y
`OpenAIEmbeddingProvider`, sin capturar errores para activar un fallback.

Modificar `_build_agent` para usar la fábrica. Añadir `/health/ready`, que
devuelva 200 cuando el agente y retrieval estén listos, y 503 con un cuerpo
genérico cuando no lo estén.

- [ ] **Step 4: Ejecutar pruebas de composición y salud**

Run: `python -m pytest tests/cv_agent/test_retrieval_factory.py tests/cv_agent/test_health.py tests/cv_agent/test_standalone.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add cv_agent/main.py cv_agent/retrieval/factory.py tests/cv_agent/test_retrieval_factory.py tests/cv_agent/test_health.py
git commit -m "Select Azure Search in production"
```

### Task 5: Esquema e ingesta controlada

**Files:**
- Create: `cv_agent/retrieval/ingest.py`
- Test: `tests/cv_agent/test_ingest.py`

- [ ] **Step 1: Escribir pruebas fallidas de documentos y sincronización**

```python
from cv_agent.knowledge.models import KnowledgeDocument
from cv_agent.retrieval.ingest import build_search_document, sync_documents


class FakeEmbeddings:
    def embed(self, text):
        return [0.1, 0.2, 0.3]


def test_build_search_document_contains_metadata_hash_and_vector():
    document = KnowledgeDocument(
        id="profile", title="Perfil", category="perfil",
        evidence_level="directa", impact_type="confirmado",
        source_kind="perfil", source="CV", text="Contenido",
    )

    result = build_search_document(document, FakeEmbeddings())

    assert result["id"] == "profile"
    assert result["content_vector"] == [0.1, 0.2, 0.3]
    assert len(result["content_hash"]) == 64
```

Agregar una prueba donde el índice contiene `old-id`, la fuente contiene
`profile`, y `sync_documents` carga `profile` y elimina `old-id`.

- [ ] **Step 2: Verificar el estado rojo**

Run: `python -m pytest tests/cv_agent/test_ingest.py -q`

Expected: FAIL porque el módulo no existe.

- [ ] **Step 3: Implementar esquema, hashes y sincronización**

Crear un esquema `SearchIndex` con campos de texto filtrables y
`SearchField(name="content_vector", type=Collection(Edm.Single),
vector_search_dimensions=dimensions,
vector_search_profile_name="profile-hnsw")`. Configurar `VectorSearch` con
HNSW. Implementar `build_search_document`, `sync_documents` y un CLI:

```bash
python -m cv_agent.retrieval.ingest --knowledge knowledge
```

El CLI debe usar `AZURE_SEARCH_ADMIN_KEY` solo para crear/validar el índice y
subir documentos, no imprimirla y devolver código distinto de cero ante un
error parcial.

- [ ] **Step 4: Ejecutar pruebas de ingesta**

Run: `python -m pytest tests/cv_agent/test_ingest.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add cv_agent/retrieval/ingest.py tests/cv_agent/test_ingest.py
git commit -m "Add controlled search index ingestion"
```

### Task 6: Aprovisionamiento Free, RBAC y despliegue

**Files:**
- Modify: `infra/azure/deploy.sh`
- Modify: `tests/cv_agent/test_deploy_script.py`

- [ ] **Step 1: Escribir pruebas fallidas del contrato de infraestructura**

Agregar aserciones para:

```python
for marker in (
    "Microsoft.Search",
    "az search service create",
    "--sku free",
    "Search Index Data Reader",
    "AZURE_SEARCH_ENDPOINT",
    "AZURE_SEARCH_INDEX",
    "AZURE_SEARCH_ADMIN_KEY",
    "/health/ready",
):
    assert marker in text

assert "--sku basic" not in text.lower()
assert "azure-search-admin-key" not in text
```

- [ ] **Step 2: Verificar el estado rojo**

Run: `python -m pytest tests/cv_agent/test_deploy_script.py -q`

Expected: FAIL porque el despliegue aún no aprovisiona Search.

- [ ] **Step 3: Extender el script con controles de costo**

Definir `SEARCH_NAME="srch-prueba-b-gael-ai"` e
`SEARCH_INDEX="cv-profile-v1"`. Registrar `Microsoft.Search`. Antes de crear,
consultar servicios Free en la suscripción mediante `az resource list
--resource-type Microsoft.Search/searchServices`; si existe otro Free y el
servicio esperado no existe, detenerse. Crear exclusivamente con `--sku free`.

Obtener temporalmente la clave administrativa con `az search admin-key show`,
ejecutar la ingesta sin imprimirla y eliminar la variable al terminar. Activar
identidad administrada en Container Apps, asignar `Search Index Data Reader`
al principal sobre el servicio y configurar endpoint e índice como variables
no secretas. Cambiar readiness a `/health/ready`.

- [ ] **Step 4: Verificar script y suite local**

Run: `bash -n infra/azure/deploy.sh && python -m pytest tests/cv_agent/test_deploy_script.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add infra/azure/deploy.sh tests/cv_agent/test_deploy_script.py
git commit -m "Provision Azure AI Search securely"
```

### Task 7: Documentación y evaluación de aceptación

**Files:**
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/DEMO.md`
- Modify: `docs/EVALUATION.md`
- Modify: `infra/azure/README.md`
- Create: `evals/azure_search_cases.jsonl`
- Test: `tests/cv_agent/test_documentation.py`

- [ ] **Step 1: Escribir prueba fallida de documentación honesta**

```python
from pathlib import Path


def test_readme_describes_active_azure_search_architecture():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "Azure AI Search" in text
    assert "identidad administrada" in text
    assert "En producción se migraría a Azure AI Search" not in text
    assert "índice en memoria" not in text
```

- [ ] **Step 2: Verificar el estado rojo**

Run: `python -m pytest tests/cv_agent/test_documentation.py -q`

Expected: FAIL por las afirmaciones actuales del README.

- [ ] **Step 3: Actualizar documentación y casos**

Describir el flujo real de Azure, la separación entre ingesta y lectura, RBAC,
los comandos operativos, el adaptador local limitado a pruebas y las decisiones
de costo. Crear casos JSONL para IA profesional, Terraform, cotizaciones,
arquitectura RAG y fuera de alcance, con IDs esperados.

- [ ] **Step 4: Ejecutar pruebas documentales y evaluación offline**

Run: `python -m pytest tests/cv_agent/test_documentation.py -q && python -m cv_agent.evaluation.runner`

Expected: PASS y métricas sobre sus umbrales.

- [ ] **Step 5: Commit**

```bash
git add README.md docs infra/azure/README.md evals/azure_search_cases.jsonl tests/cv_agent/test_documentation.py
git commit -m "Document production search architecture"
```

### Task 8: Verificación local completa

**Files:**
- No code changes expected.

- [ ] **Step 1: Ejecutar toda la suite**

Run: `python -m pytest -q`

Expected: todas las pruebas pasan.

- [ ] **Step 2: Ejecutar evaluación**

Run: `python -m cv_agent.evaluation.runner`

Expected: todos los umbrales pasan.

- [ ] **Step 3: Validar imagen**

Run: `docker build -t prueba-b-gael-ai:azure-search .`

Expected: exit 0 y la imagen conserva el usuario no privilegiado.

- [ ] **Step 4: Revisar seguridad y árbol de trabajo**

Run: `git diff --check && git status --short && git grep -nE 'sk-[A-Za-z0-9_-]{16,}|AZURE_SEARCH_ADMIN_KEY=' -- ':!docs/AZURE_AI_SEARCH_IMPLEMENTATION_PLAN.md'`

Expected: sin errores, secretos ni cambios inesperados.

### Task 9: Crear recursos e ingerir conocimiento

**Files:**
- Azure subscription: `Enerey-Prod`

- [ ] **Step 1: Confirmar contexto exacto**

Run: `az account show --query '{name:name,user:user.name,id:id}' -o table`

Expected: `Enerey-Prod`, `appenerey@gmail.com`, suscripción
`5825f561-1940-4b7e-8219-b85800fcc7e6`.

- [ ] **Step 2: Ejecutar despliegue con confirmación explícita**

```bash
EXPECTED_SUBSCRIPTION="Enerey-Prod" \
CONFIRM_AZURE_CONTEXT=YES \
OPENAI_API_KEY="$OPENAI_API_KEY" \
AGENT_API_KEY="$AGENT_API_KEY" \
bash infra/azure/deploy.sh
```

Expected: servicio Search Free, índice sincronizado y revisión nueva de
Container Apps. Si Free no está disponible, detenerse sin crear un SKU pago.

- [ ] **Step 3: Verificar RBAC e índice sin revelar claves**

Run: `az role assignment list --scope "$(az search service show -g rg-prueba-b-gael-ai -n srch-prueba-b-gael-ai --query id -o tsv)" --query "[].{role:roleDefinitionName,principal:principalId}" -o table`

Expected: identidad de Container Apps con `Search Index Data Reader`.

### Task 10: Pruebas públicas, publicación y evidencia final

**Files:**
- GitHub repository: `GaelAlguiar/banorte-llm-agent`

- [ ] **Step 1: Validar sondas públicas**

Run: `curl -fsS https://ca-prueba-b-gael-ai.agreeablefield-a028190c.eastus.azurecontainerapps.io/health && curl -fsS https://ca-prueba-b-gael-ai.agreeablefield-a028190c.eastus.azurecontainerapps.io/health/ready`

Expected: `status=ok` y `status=ready`.

- [ ] **Step 2: Ejecutar las cinco consultas de aceptación**

Enviar solicitudes autenticadas a `/v1/responses` para IA laboral, Terraform,
cotizaciones, arquitectura y fuera de alcance. Verificar respuestas 200,
evidencia correcta y rechazo de la pregunta no relacionada, sin mostrar el
token en logs ni documentación.

- [ ] **Step 3: Confirmar que Azure atendió las consultas**

Revisar la disponibilidad del índice y los logs allowlistados de la revisión.
No aceptar como evidencia únicamente una respuesta del LLM; `/health/ready` y
la ausencia de fallback deben probar que el backend Azure estuvo activo.

- [ ] **Step 4: Publicar commits**

Run: `git push origin main`

Expected: rama pública actualizada bajo el perfil `GaelAlguiar`.

- [ ] **Step 5: Verificar CI y estado final**

Run: `gh run watch --repo GaelAlguiar/banorte-llm-agent --exit-status && git status --short`

Expected: CI exitoso y árbol limpio.
