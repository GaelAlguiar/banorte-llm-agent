# Response Contract Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, offline response-contract fixture evaluator without changing the existing routing/retrieval matrix or UI suggestions.

**Architecture:** Keep answer-quality scoring in a new module and fixture file. Validate explicit observable contracts, aggregate contract/category metrics, and enforce category floors plus zero core failures.

**Tech Stack:** Python 3.14, JSONL, pytest.

---

### Task 1: Define the evaluator contract with failing tests

**Files:**
- Create: `tests/cv_agent/test_response_contract_evaluation.py`

- [ ] Test valid representative fixtures, category floors, core zero tolerance, duplicate IDs, bad provenance, and individual contract failures.
- [ ] Run the focused test and confirm it fails because the evaluator module does not exist.

### Task 2: Implement deterministic scoring and curated fixtures

**Files:**
- Create: `cv_agent/evaluation/response_contracts.py`
- Create: `evals/response_contract_cases.jsonl`

- [ ] Implement schema validation and contract checks required by the tests.
- [ ] Add representative fixtures across all requested categories with authorized document IDs.
- [ ] Run focused tests and the response-contract CLI until green.

### Task 3: Document limitations and verify regressions

**Files:**
- Modify: `docs/EVALUATION.md`
- Modify: `README.md`

- [ ] Document that fixtures are offline policy examples, not real OpenAI prose, and require a one-shot production smoke.
- [ ] Run the full suite, existing 125-case evaluation, response-contract evaluation, immutable-input hash checks, C# absence scan, and diff audit.
- [ ] Commit, push, request review, and open a draft PR without merging or deploying.
