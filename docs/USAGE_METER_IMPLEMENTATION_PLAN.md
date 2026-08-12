# Per-Response Usage Meter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mostrar exactamente `1,234 tokens · 67.2% disponible` dos saltos de línea debajo de cada respuesta que consuma OpenAI, sin exponer importes monetarios.

**Architecture:** `OpenAIResponsesModel` devolverá texto y uso real como un valor estructurado. `CvAgentService` enviará ese uso a un medidor inyectado que calcula el costo internamente y actualiza de forma idempotente un almacén local o Azure Table; después adjuntará un único pie visible y valores estructurados al `AgentAnswer`. JSON, SSE, Flask y el frontend compartirán el mismo resultado, y los clientes nunca podrán controlar presupuesto, tarifas o saldo.

**Tech Stack:** Python 3.12, OpenAI Responses SDK, FastAPI/Open Responses, Flask/JavaScript, Azure Table Storage con Managed Identity, pytest y Azure CLI.

---

## File structure

- Create `cv_agent/usage/models.py`: tipos inmutables para uso, tarifas y estado público.
- Create `cv_agent/usage/meter.py`: cálculo interno, formato y orquestación idempotente.
- Create `cv_agent/usage/store.py`: protocolo, almacén en memoria y Azure Table con ETag/transacción.
- Modify `cv_agent/agent/openai_model.py`: extraer el objeto `usage` real del SDK.
- Modify `cv_agent/agent/service.py`: registrar una sola generación y adjuntar un único pie.
- Modify `cv_agent/api/responses.py`: serializar uso/presupuesto con paridad JSON/SSE.
- Modify `cv_agent/web/app.py`, `cv_agent/web/static/chat.js` y `chat.css`: transportar, persistir y presentar el uso sin duplicación.
- Modify `cv_agent/config.py`, `cv_agent/main.py`, `requirements.txt`, `.env.example`: configuración validada e inyección.
- Modify `infra/azure/deploy.sh` y `infra/azure/README.md`: tabla, RBAC, secretos y despliegue.
- Add/modify focused tests under `tests/cv_agent/` for each boundary.

### Task 1: Capture real per-response usage

**Files:**
- Create: `cv_agent/usage/__init__.py`
- Create: `cv_agent/usage/models.py`
- Modify: `cv_agent/agent/openai_model.py`
- Test: `tests/cv_agent/test_openai_model.py`

- [ ] **Step 1: Write failing SDK usage tests**

Add tests whose fake Responses object includes:

```python
usage=SimpleNamespace(
    input_tokens=1200,
    output_tokens=234,
    total_tokens=1434,
    input_tokens_details=SimpleNamespace(cached_tokens=200),
    output_tokens_details=SimpleNamespace(reasoning_tokens=80),
)
```

Assert that `generate()` returns a `ModelGeneration` with text plus
`TokenUsage(input_tokens=1200, cached_input_tokens=200,
output_tokens=234, reasoning_tokens=80, total_tokens=1434)`. Add cases for a
missing usage object and inconsistent/negative fields; both must return
`usage=None`, never invented values.

- [ ] **Step 2: Run RED**

Run:

```bash
python3 -m pytest tests/cv_agent/test_openai_model.py -q
```

Expected: FAIL because `ModelGeneration` and `TokenUsage` do not exist and
`generate()` still returns a string.

- [ ] **Step 3: Add immutable usage models**

Implement:

```python
@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    total_tokens: int

@dataclass(frozen=True)
class ModelGeneration:
    text: str
    usage: TokenUsage | None
```

Add a private parser that accepts only non-boolean integers, requires every
value to be nonnegative, enforces cached input `<= input`, reasoning `<= output`
and `total == input + output`, and otherwise returns `None`. Return
`ModelGeneration(response.output_text, parsed_usage)`.

- [ ] **Step 4: Adapt existing model fakes and run GREEN**

Update fake model returns in tests to `ModelGeneration(text=..., usage=None)`.
Run the focused suite and expect PASS.

- [ ] **Step 5: Commit**

```bash
git add cv_agent/usage cv_agent/agent/openai_model.py tests/cv_agent
git commit -m "Capture per-response OpenAI usage"
```

### Task 2: Calculate and persist the available percentage

**Files:**
- Create: `cv_agent/usage/meter.py`
- Create: `cv_agent/usage/store.py`
- Test: `tests/cv_agent/test_usage_meter.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Write failing pricing and in-memory store tests**

Cover this public result and internal calculation:

```python
result = meter.record(
    event_id="response-1",
    usage=TokenUsage(1200, 200, 234, 80, 1434),
)
assert result.total_tokens == 1434
assert result.available_percent == 67.1
assert format_usage_footer(result) == "1,434 tokens · 67.1% disponible"
```

Use decimal rates per million tokens and assert cached input is subtracted
from ordinary input before applying its discounted rate. Add duplicate
`event_id`, two concurrent records, lower/upper percentage bounds, and a store
failure that returns tokens but `available_percent=None`.

- [ ] **Step 2: Run RED**

```bash
python3 -m pytest tests/cv_agent/test_usage_meter.py -q
```

Expected: FAIL because the usage meter modules are missing.

- [ ] **Step 3: Implement the protocol and pure calculation**

Define:

```python
@dataclass(frozen=True)
class ModelRates:
    input_per_million: Decimal
    cached_input_per_million: Decimal
    output_per_million: Decimal

@dataclass(frozen=True)
class PublicUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    available_percent: float | None

class UsageBudgetStore(Protocol):
    def apply_once(self, event_id: str, cost: Decimal) -> Decimal: ...
```

`UsageMeter.record()` must calculate with `Decimal`, call `apply_once`, clamp
the returned available fraction, round it to one decimal and catch only the
store's typed `UsageStoreError`. `format_usage_footer()` uses comma-separated
integer formatting and returns no footer when the percentage is absent.

- [ ] **Step 4: Implement in-memory and Azure stores atomically**

The in-memory store uses a lock and a set of event IDs. `AzureTableUsageStore`
loads one aggregate entity and submits one same-partition transaction:

```python
[
    ("update", aggregate, {"etag": etag,
      "match_condition": MatchConditions.IfNotModified}),
    ("create", {"PartitionKey": "usage", "RowKey": event_id,
      "cost": str(cost)}),
]
```

On 409, read the ledger row and return the existing aggregate; on 412, retry a
bounded five times with a fresh ETag. Never log cost or entity values. Add
`azure-data-tables>=12.6,<13` to requirements.

- [ ] **Step 5: Run GREEN and commit**

```bash
python3 -m pytest tests/cv_agent/test_usage_meter.py -q
git add cv_agent/usage requirements.txt tests/cv_agent/test_usage_meter.py
git commit -m "Persist usage budget atomically"
```

### Task 3: Add one usage footer to each generated answer

**Files:**
- Modify: `cv_agent/agent/service.py`
- Modify: `cv_agent/main.py`
- Test: `tests/cv_agent/test_agent_policy.py`
- Test: `tests/cv_agent/test_security.py`

- [ ] **Step 1: Write failing service tests**

Inject a recording `UsageMeter` and a model returning real usage. Assert:

```python
assert answer.text.endswith("\n\n1,234 tokens · 67.2% disponible")
assert answer.usage.total_tokens == 1234
assert answer.usage.available_percent == 67.2
```

Also assert: the event ID is generated server-side; one model generation causes
one store update; an out-of-scope deterministic redirect has `usage=None` and
no footer; missing SDK usage leaves the original answer unchanged; and the
footer never contains `$`, `USD`, budget size, rates or spent amount.

- [ ] **Step 2: Run RED**

```bash
python3 -m pytest tests/cv_agent/test_agent_policy.py tests/cv_agent/test_security.py -q
```

Expected: FAIL because `AgentAnswer` has no usage and the model result is still
treated as a string.

- [ ] **Step 3: Update the model protocol and service**

Add `usage: PublicUsage | None = None` to `AgentAnswer`. Change `ModelClient`
to return `ModelGeneration`. After generation, strip only the model text,
record usage once with `uuid.uuid4().hex`, and append exactly:

```python
footer = format_usage_footer(public_usage)
text = f"{generation.text.strip()}\n\n{footer}" if footer else generation.text.strip()
```

Do not meter classifiers, embeddings or deterministic responses. Build and
inject the meter in `main.py`; use an in-memory store locally and the Azure
store only when its complete configuration is present.

- [ ] **Step 4: Run GREEN and commit**

```bash
python3 -m pytest tests/cv_agent/test_agent_policy.py tests/cv_agent/test_security.py -q
git add cv_agent/agent cv_agent/main.py tests/cv_agent
git commit -m "Attach usage footer to generated answers"
```

### Task 4: Preserve Open Responses JSON and SSE parity

**Files:**
- Modify: `cv_agent/api/responses.py`
- Test: `tests/cv_agent/test_responses_contract.py`
- Test: `tests/cv_agent/test_api_token_controls.py`

- [ ] **Step 1: Write failing JSON/SSE contract tests**

For a stub answer with `PublicUsage`, assert JSON contains real standard usage:

```json
"usage": {"input_tokens": 1000, "output_tokens": 234,
          "total_tokens": 1234}
```

and the safe extension:

```json
"budget": {"available_percent": 67.2}
```

Parse `response.completed` from SSE and assert identical values and identical
single footer. Add a missing-usage case that preserves the current zero-valued
Open Responses usage and omits `budget` and the footer.

- [ ] **Step 2: Run RED**

```bash
python3 -m pytest tests/cv_agent/test_responses_contract.py tests/cv_agent/test_api_token_controls.py -q
```

Expected: FAIL because `_completed_response()` always emits zero usage and no
budget.

- [ ] **Step 3: Serialize the answer usage once**

Pass `answer.usage` into `_completed_response()` and `_stream_events()`. Keep
all metadata string limits intact. Serialize only token counters and the one
percentage; never add internal cost/rate fields.

- [ ] **Step 4: Run GREEN and commit**

```bash
python3 -m pytest tests/cv_agent/test_responses_contract.py tests/cv_agent/test_api_token_controls.py -q
git add cv_agent/api/responses.py tests/cv_agent
git commit -m "Expose safe usage in Open Responses"
```

### Task 5: Render and persist the footer in the Flask chat

**Files:**
- Modify: `cv_agent/web/app.py`
- Modify: `cv_agent/web/static/chat.js`
- Modify: `cv_agent/web/static/chat.css`
- Test: `tests/cv_agent/test_flask_ui.py`

- [ ] **Step 1: Write failing transport and UI tests**

Assert Flask returns `usage` and `budget`, while `response` already contains
one footer. Assert JavaScript stores usage with the message, identifies the
final footer rather than creating a second string, and renders class
`message-usage` with accessible text. Assert the exact literal
`tokens · ${percent}% disponible`, two-line separation, localStorage reload,
mobile layout, and absence of `$`, `USD` and internal field names.

- [ ] **Step 2: Run RED**

```bash
python3 -m pytest tests/cv_agent/test_flask_ui.py -q
```

Expected: FAIL because Flask and chat history omit usage.

- [ ] **Step 3: Add safe Flask fields and nonduplicating rendering**

Return:

```python
"usage": ({"input_tokens": ..., "output_tokens": ...,
           "total_tokens": ...} if answer.usage else None),
"budget": ({"available_percent": ...}
           if answer.usage and answer.usage.available_percent is not None
           else None),
```

Store those objects with assistant messages. Split the already-present final
footer from display text using an anchored pattern, render it in a `<p
class="message-usage">`, and leave plain text unchanged if it does not match.
This makes our frontend visually secondary while the Banorte portal still sees
the footer in the text.

- [ ] **Step 4: Run GREEN and commit**

```bash
python3 -m pytest tests/cv_agent/test_flask_ui.py -q
git add cv_agent/web tests/cv_agent/test_flask_ui.py
git commit -m "Render per-response usage in chat"
```

### Task 6: Validate private configuration and Azure persistence

**Files:**
- Modify: `cv_agent/config.py`
- Modify: `.env.example`
- Modify: `infra/azure/deploy.sh`
- Modify: `infra/azure/README.md`
- Test: `tests/cv_agent/test_config.py`
- Test: `tests/cv_agent/test_deploy_script.py`

- [ ] **Step 1: Write failing configuration and deploy tests**

Test that usage metering is disabled unless all private settings exist; decimal
rates are positive; total budget is positive; initial spent is within budget;
table/account names are validated; and secrets cannot equal API keys. Inspect
the deploy script to require `Microsoft.Storage`, a Standard_LRS storage
account, a table, `Storage Table Data Contributor`, Managed Identity, and
secret references for budget/rates in both create and update paths. Assert the
script never echoes those values.

- [ ] **Step 2: Run RED**

```bash
python3 -m pytest tests/cv_agent/test_config.py tests/cv_agent/test_deploy_script.py -q
```

Expected: FAIL because usage settings and Storage resources do not exist.

- [ ] **Step 3: Add validated settings and deployment wiring**

Add optional environment settings for storage account/table, total budget,
initial spent and three token rates. Parse monetary values as `Decimal` from
strings. Fail closed in production if metering is explicitly enabled but any
value is missing. In `deploy.sh`, create/reuse a named storage account supplied
through `USAGE_STORAGE_ACCOUNT`, create the table, assign RBAC to the Container
App identity and pass monetary configuration exclusively through Container App
secret references. `.env.example` and docs show empty placeholders only; they
must not reveal amounts.

- [ ] **Step 4: Run GREEN, shell validation and commit**

```bash
python3 -m pytest tests/cv_agent/test_config.py tests/cv_agent/test_deploy_script.py -q
bash -n infra/azure/deploy.sh
git add cv_agent/config.py .env.example infra/azure tests/cv_agent
git commit -m "Provision persistent usage accounting"
```

### Task 7: Full verification, privacy audit and publication

**Files:**
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/BANORTE_PLATFORM_CONTRACT.md`
- Test: `tests/cv_agent/test_documentation.py`
- Test: `tests/cv_agent/test_public_content.py`

- [ ] **Step 1: Add failing documentation/privacy tests**

Require the exact visible format, clarify that it is per final generation, and
state that the percentage is an internal demo meter rather than OpenAI's
official billing balance. Assert public response examples contain no dollar
amounts, spent amount, budget total, rates, keys, storage endpoints or account
identifiers.

- [ ] **Step 2: Run RED and update documentation**

```bash
python3 -m pytest tests/cv_agent/test_documentation.py tests/cv_agent/test_public_content.py -q
```

Update the three docs with the public contract, limitations and safe operations
procedure; rerun and expect PASS.

- [ ] **Step 3: Run all verification gates**

```bash
python3 -m pytest tests/cv_agent -q
python3 -m cv_agent.evaluation.runner
python3 -m cv_agent.evaluation.answer_contract_runner
bash -n infra/azure/deploy.sh
git diff --check
```

Expected: all tests pass, both evaluators report `core_failure_count: 0`, shell
syntax is valid and diff check is clean.

- [ ] **Step 4: Run explicit privacy and UI assertions**

```bash
rg -n '\$|USD|USAGE_.*RATE|USAGE_.*BUDGET' cv_agent/web cv_agent/api
rg -n '1,234 tokens · 67\.2% disponible' tests docs
```

Expected: no monetary/internal configuration in public response/UI code; exact
format is covered by tests and docs.

- [ ] **Step 5: Commit and request review**

```bash
git add README.md docs tests
git commit -m "Document safe per-response usage"
```

Request independent specification and quality/security reviews before merging.
After both approve and CI is green, squash-merge. Deployment then performs one
storage migration, one Container App revision, and one live response check that
confirms the footer appears exactly once in the Banorte portal.
