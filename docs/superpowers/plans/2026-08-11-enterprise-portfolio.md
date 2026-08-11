# Enterprise Portfolio Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the CV agent with specific, privacy-safe HeyTech and Banregio stories, aligned prompts, and production RAG evidence.

**Architecture:** Add four sanitized knowledge documents so retrieval selects precise enterprise stories instead of one broad profile. Extend existing skill allowlists, response policy, Flask suggestions, and the JSONL evaluation matrix without changing the Open Responses contract. Validate locally, reindex Azure AI Search, deploy the tested revision, and synchronize the external platform.

**Tech Stack:** Python, FastAPI, Flask/Jinja, OpenAI Responses API, Azure AI Search, Azure Container Apps, pytest, GitHub Actions, Azure CLI.

---

## File map

- Create `knowledge/13_heytech_apim_chatbot.md`: APIM facade and chatbot orchestration.
- Create `knowledge/14_heytech_terraform_multicloud.md`: Terraform and multicloud VPN.
- Create `knowledge/15_heytech_ia_plataforma.md`: document AI and platform ecosystem.
- Create `knowledge/16_entrega_jira.md`: Jira delivery by sprint.
- Modify `cv_agent/skills/catalog/*.yaml`: authorize only relevant new sources.
- Modify `cv_agent/agent/prompts.py`: require provenance-aware stories.
- Modify `cv_agent/web/templates/chat.html`: replace eight suggestions.
- Modify `evals/cv_agent_cases.jsonl`, `docs/EVALUATION.md`, and `docs/DEMO.md`.
- Modify focused tests under `tests/cv_agent/`.

### Task 1: Add sanitized enterprise knowledge

**Files:**
- Create: `knowledge/13_heytech_apim_chatbot.md`
- Create: `knowledge/14_heytech_terraform_multicloud.md`
- Create: `knowledge/15_heytech_ia_plataforma.md`
- Create: `knowledge/16_entrega_jira.md`
- Test: `tests/cv_agent/test_knowledge.py`

- [ ] **Step 1: Write failing document and privacy tests**

Append:

```python
def test_enterprise_portfolio_contains_sanitized_stories():
    documents = {item.id: item for item in load_knowledge(Path("knowledge"))}
    expected = {
        "heytech-apim-chatbot",
        "heytech-terraform-multicloud",
        "heytech-ia-plataforma",
        "entrega-jira-sprints",
    }
    assert expected <= documents.keys()
    assert all(documents[item].source_kind == "laboral" for item in expected)


def test_enterprise_portfolio_omits_private_details():
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("knowledge").glob("1[3-6]_*.md")
    ).casefold()
    forbidden = (
        "http://", "https://", "terraform.tfvars",
        "subscription-key", "personal access token", "10.0.",
    )
    assert not any(marker in text for marker in forbidden)
```

- [ ] **Step 2: Verify the test fails**

Run `python -m pytest tests/cv_agent/test_knowledge.py::test_enterprise_portfolio_contains_sanitized_stories -v`.

Expected: FAIL because the four IDs do not exist.

- [ ] **Step 3: Create APIM/chatbot knowledge**

Use front matter:

```yaml
id: heytech-apim-chatbot
title: Fachada segura de APIM y orquestación del chatbot HeyTech
category: proyecto
evidence_level: directa
impact_type: inferido
source_kind: laboral
source: Autoría verificable en PR empresarial y participación confirmada
```

The body must state that Gael built a Java Azure Function before APIM to centralize JWT identity, Managed Identity, protected subscription resolution, routing, header filtering, tests, and documentation. A second section must describe confirmed participation in chatbot communication and orchestration. Do not include repository names, class names, internal routes, headers, URLs, or identifiers.

- [ ] **Step 4: Create Terraform/multicloud knowledge**

Use ID `heytech-terraform-multicloud`, `category: proyecto`, `evidence_level: directa`, `impact_type: inferido`, and `source_kind: laboral`. Describe verifiable modularization for network, apps, data, IAM, security, bastion, Redis, and shared resources; then Azure-AWS and Azure-GCP Site-to-Site VPN work with gateways, BGP, routes, environments, and validation. State qualitative reuse/reviewability impact without network ranges.

- [ ] **Step 5: Create document-AI/platform knowledge**

Use ID `heytech-ia-plataforma`. Describe confirmed participation in Python PDF analysis for constancias and comprobantes, containers, tests, PostgreSQL/Alembic, and Azure deployment. Add the related Java services, payments, cloud guardrails, APIM policies, and Angular dashboard as a platform story. Do not imply exclusive authorship.

- [ ] **Step 6: Create Jira delivery knowledge**

Use ID `entrega-jira-sprints`, `category: historia`, and direct labor evidence. Explain stories, technical subtasks, dependencies, blockers, testing, documentation, deliverables, and cross-team coordination in each sprint.

- [ ] **Step 7: Run and commit**

```bash
python -m pytest tests/cv_agent/test_knowledge.py -q
git add knowledge/13_heytech_apim_chatbot.md knowledge/14_heytech_terraform_multicloud.md knowledge/15_heytech_ia_plataforma.md knowledge/16_entrega_jira.md tests/cv_agent/test_knowledge.py
git commit -m "Add sanitized enterprise project stories"
```

Expected: all knowledge tests pass.

### Task 2: Authorize the new sources in skills

**Files:**
- Modify: `cv_agent/skills/catalog/project_story.yaml`
- Modify: `cv_agent/skills/catalog/architecture_explainer.yaml`
- Modify: `cv_agent/skills/catalog/profile_summary.yaml`
- Test: `tests/cv_agent/test_skills.py`

- [ ] **Step 1: Write the failing allowlist test**

```python
def test_enterprise_sources_are_available_to_relevant_skills():
    skills = {skill.name: skill for skill in load_skills()}
    assert "knowledge/13_heytech_apim_chatbot.md" in skills["project_story"].allowed_sources
    assert "knowledge/14_heytech_terraform_multicloud.md" in skills["architecture_explainer"].allowed_sources
    assert "knowledge/15_heytech_ia_plataforma.md" in skills["project_story"].allowed_sources
    assert "knowledge/16_entrega_jira.md" in skills["profile_summary"].allowed_sources
```

- [ ] **Step 2: Verify failure**

Run `python -m pytest tests/cv_agent/test_skills.py::test_enterprise_sources_are_available_to_relevant_skills -v`.

Expected: FAIL because paths are absent.

- [ ] **Step 3: Extend allowlists minimally**

Add all four paths to `project_story.yaml`; add files 13, 14, and 15 to `architecture_explainer.yaml`; add all four to `profile_summary.yaml`. Keep network and shell access disabled.

- [ ] **Step 4: Run and commit**

```bash
python -m pytest tests/cv_agent/test_skills.py -q
git add cv_agent/skills/catalog tests/cv_agent/test_skills.py
git commit -m "Allow enterprise stories in agent skills"
```

### Task 3: Require specific, provenance-aware answers

**Files:**
- Modify: `cv_agent/agent/prompts.py`
- Test: `tests/cv_agent/test_agent_policy.py`

- [ ] **Step 1: Add failing tests**

```python
def test_instructions_distinguish_authorship_from_participation():
    instructions = " ".join(build_instructions().split())
    assert "autoría verificable" in instructions
    assert "participación confirmada" in instructions
    assert "autoría exclusiva" in instructions
    assert "código propietario" in instructions


def test_enterprise_questions_retrieve_specific_stories():
    agent, model = build_agent()
    agent.answer("¿Cómo diseñó Gael una fachada segura con Azure Functions y APIM?")
    assert model.calls[0]["evidence"][0]["document_id"] == "heytech-apim-chatbot"
    agent.answer("¿Cómo organizaba historias y subtareas en Jira por sprint?")
    assert model.calls[1]["evidence"][0]["document_id"] == "entrega-jira-sprints"
```

- [ ] **Step 2: Verify failure**

Run both tests with `python -m pytest ... -v`. Expected: policy text or retrieval ranking fails.

- [ ] **Step 3: Extend instructions**

Insert this policy after the source-kind paragraph:

```text
Cuando la evidencia indique autoría verificable, puedes explicar que Gael
diseñó o desarrolló esa contribución. Cuando indique participación confirmada,
describe su colaboración sin atribuirle autoría exclusiva del repositorio o
del trabajo del equipo. Explica la arquitectura a nivel profesional, pero no
reveles código propietario, nombres internos, rutas, identificadores, URLs
privadas ni topología sensible.
```

- [ ] **Step 4: Run and commit**

```bash
python -m pytest tests/cv_agent/test_agent_policy.py tests/cv_agent/test_retrieval.py -q
git add cv_agent/agent/prompts.py tests/cv_agent/test_agent_policy.py
git commit -m "Ground enterprise answers in contribution provenance"
```

### Task 4: Replace the eight suggested questions

**Files:**
- Modify: `cv_agent/web/templates/chat.html:34-42`
- Test: `tests/cv_agent/test_flask_ui.py`

- [ ] **Step 1: Replace old assertions with the exact set**

```python
suggestions = (
    "¿Qué proyectos empresariales demuestran mejor la experiencia de Gael con IA, cloud e integración?",
    "¿Cómo diseñó Gael una fachada segura entre clientes, Azure Functions y APIM?",
    "¿Qué experiencia tiene Gael construyendo infraestructura modular con Terraform en Azure?",
    "¿Cómo implementó conectividad multicloud entre Azure, AWS y Google Cloud?",
    "¿Qué participación tuvo Gael en el chatbot y los servicios de análisis de documentos con IA de HeyTech?",
    "¿Cómo trabajó Gael con microservicios Java, seguridad cloud, pagos y políticas de APIM?",
    "¿Cómo organizaba Gael historias, subtareas, dependencias y entregables mediante Jira en cada sprint?",
    "¿Por qué esta experiencia convierte a Gael en un candidato valioso para un equipo de IA empresarial?",
)
assert response.text.count('class="suggestion"') == len(suggestions)
assert all(question in response.text for question in suggestions)
```

- [ ] **Step 2: Verify the UI test fails**

Run `python -m pytest tests/cv_agent/test_flask_ui.py::test_chat_page_is_served_by_flask_without_secrets -v`.

- [ ] **Step 3: Replace the buttons**

Put the tuple's eight questions into the eight existing suggestion buttons. Preserve their markup and accessibility attributes.

- [ ] **Step 4: Run and commit**

```bash
python -m pytest tests/cv_agent/test_flask_ui.py -q
git add cv_agent/web/templates/chat.html tests/cv_agent/test_flask_ui.py
git commit -m "Update enterprise portfolio suggestions"
```

### Task 5: Expand evaluation and demonstration coverage

**Files:**
- Modify: `evals/cv_agent_cases.jsonl`
- Modify: `docs/EVALUATION.md`
- Modify: `docs/DEMO.md`
- Test: `tests/cv_agent/test_evaluation.py`

- [ ] **Step 1: Append six JSONL cases**

Add IDs `enterprise-01` through `enterprise-06` for: APIM facade, Terraform modularization, Azure/AWS/GCP connectivity, PDF AI, Jira delivery, and a privacy attack requesting internal routes. Each case must name the expected new document, required public terms, forbidden sensitive terms, expected skill, and category. The privacy case expects no documents and `privacy_guard`.

- [ ] **Step 2: Update documentation**

Change `docs/EVALUATION.md` from 40 to 46 cases and add APIM, Terraform, multicloud, document AI, and Jira to its coverage. Replace the first enterprise questions in `docs/DEMO.md` with the new suggestions.

- [ ] **Step 3: Run evaluation without lowering thresholds**

```bash
python -m cv_agent.evaluation.runner
```

Expected: exit 0, 46 cases, and all metrics meet `THRESHOLDS`. If retrieval fails, improve document wording or correct an objectively wrong expected route; do not lower thresholds.

- [ ] **Step 4: Run tests and commit**

```bash
python -m pytest tests/cv_agent/test_evaluation.py -q
git add evals/cv_agent_cases.jsonl docs/EVALUATION.md docs/DEMO.md
git commit -m "Expand enterprise portfolio evaluation"
```

### Task 6: Validate and publish

**Files:**
- Verify: all changed files

- [ ] **Step 1: Scan formatting and secrets**

```bash
git diff --check origin/main...HEAD
rg -n 'gho_|sk-proj-|BEGIN PRIVATE KEY|personal access token|10\.0\.' knowledge docs evals cv_agent tests
```

Expected: no diff errors and no sensitive values in new content.

- [ ] **Step 2: Run the full suite**

```bash
python -m pytest tests/cv_agent -q
python -m cv_agent.evaluation.runner
```

Expected: all tests and thresholds pass.

- [ ] **Step 3: Push and open a draft PR**

```bash
git push -u origin agent/enterprise-portfolio
gh auth switch --hostname github.com --user GaelAlguiar
gh pr create --draft --base main --head agent/enterprise-portfolio --title "Expand enterprise project portfolio" --body-file /tmp/enterprise-portfolio-pr.md
```

The PR body must summarize sanitized stories, provenance, prompt alignment, evaluation results, and privacy checks.

- [ ] **Step 4: Merge only after CI passes**

```bash
gh pr checks --watch
gh pr ready
gh pr merge --squash
```

Expected: CI succeeds and the PR becomes MERGED.

### Task 7: Reindex, deploy, and synchronize the platform

**Files:**
- Runtime configuration only; never commit secrets.

- [ ] **Step 1: Verify Azure context**

```bash
az account show --query '{subscription:name,tenant:tenantId,user:user.name}' -o table
```

Expected: approved `Enerey-Prod` context. Stop on any mismatch.

- [ ] **Step 2: Reindex sanitized knowledge**

Load the Search admin key without printing it, then run:

```bash
export AZURE_SEARCH_ENDPOINT="https://srch-prueba-b-gael-ai.search.windows.net"
export AZURE_SEARCH_INDEX="cv-profile-v1"
python -m cv_agent.retrieval.ingest --knowledge knowledge
unset AZURE_SEARCH_ADMIN_KEY
```

Expected: complete authorized document count and no credential output.

- [ ] **Step 3: Deploy the merged revision**

```bash
git switch main
git pull --ff-only origin main
export EXPECTED_SUBSCRIPTION="Enerey-Prod"
export CONFIRM_AZURE_CONTEXT=YES
bash infra/azure/deploy.sh
```

Expected: immutable image, ready Container Apps revision, and public endpoint.

- [ ] **Step 4: Validate production**

```bash
curl --fail --silent https://ca-prueba-b-gael-ai.agreeablefield-a028190c.eastus.azurecontainerapps.io/health/ready
```

Send authenticated Open Responses requests for APIM, Terraform, document AI, and Jira. Expected: HTTP 200, specific answers, and no internal details.

- [ ] **Step 5: Synchronize platform prompts**

Open the registered agent, replace suggestions with the exact Task 4 tuple, keep endpoint, key, multimodal toggles, and extra parameters unchanged, then save. Expected: eight suggestions appear and a test chat returns a specific enterprise story.

- [ ] **Step 6: Record non-sensitive evidence**

Document merged commit, CI status, deployed revision, Search document count, and tested questions. Do not publish account emails, subscription IDs, keys, or private repository information.
