# Offline response-contract evaluation design

## Scope

Add a deterministic evaluation layer for curated, representative answer fixtures. It is separate from the existing `EvidenceModel` matrix, which remains responsible for routing and retrieval. The new layer does not call OpenAI and makes no claim about production prose; a one-shot production smoke remains required before release.

## Architecture

`evals/response_contract_cases.jsonl` stores auditable questions, representative responses, authorized evidence provenance, and explicit expectations. `cv_agent.evaluation.response_contracts` validates the fixture schema, scores observable answer properties, writes a JSON report, and enforces both category floors and a zero-failure core gate. The existing 125-case matrix and eight UI suggestions are immutable inputs and are not edited.

The scorer checks directness and relevance, approved evidence references, Direct/Related/Transferable labeling when required, project/problem/action/result facets when evidence supports them, absence of negative denial boilerplate for authorized evidence, Junior positioning, reviewed forbidden/unsupported/numeric sentinels, sensitive disclosures, and concise professional structure. Sentinel matching is not general hallucination or semantic-grounding detection. Contract rates use only applicable fixtures and expose their numerators and denominators. Category coverage includes direct experience/project, Junior role fit, adjacent or unknown technology transfer, confirmed-only behavioral/STAR, security/privacy, out-of-scope redirects, and multimodal vacancy/CV/project/architecture comparisons.

## Acceptance

Every core fixture must pass every required contract, every category must meet its configured floor, duplicate IDs and unrecognized provenance are rejected, and reports expose per-contract and per-category results. Tests demonstrate RED before implementation and GREEN afterward. Full tests, both evaluations, C# absence, immutable-input hashes, and the final diff are checked before a draft PR; no merge or deployment is performed.
