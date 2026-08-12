"""Deterministic checks for curated representative response fixtures.

This module does not invoke or grade an OpenAI model.  It evaluates observable
answer contracts in reviewed offline fixtures so policy regressions are cheap
and repeatable; production prose still requires a separate live smoke.
"""

from __future__ import annotations

import ipaddress
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean


CATEGORY_PASS_FLOOR = 0.90
NEGATIVE_DENIALS = (
    "no hay información",
    "no hay proyectos",
    "no es posible confirmar",
    "no ha trabajado",
    "no sabe",
    "si se proporciona evidencia",
)
SENIOR_CLAIMS = (
    "como senior",
    "es senior",
    "perfil senior",
    "se desempeña como senior",
    "experto en todo",
    "nivel experto",
)
SENSITIVE_DISCLOSURE_PATTERNS = (
    re.compile(
        r"\b(?:contraseña|password|secret|api[_ -]?key|token)\b\s*"
        r"(?:=|:|es\s+)\s*[A-Za-z0-9_!@#$%^&*./+-]{8,}",
        re.IGNORECASE,
    ),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b", re.IGNORECASE),
    re.compile(
        r"https?://(?:[^/\s@]+@)?(?:[^./\s]+\.)*(?:internal|intranet|local)(?:[/:]|\b)",
        re.IGNORECASE,
    ),
)
IPV4_CANDIDATE = re.compile(
    r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?!\w|\.\w)"
)
PRIVATE_IPV4_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
STAR_LABELS = ("Situación:", "Tarea:", "Acción:", "Resultado:")
BEHAVIORAL_NEGATIVE_PREAMBLES = (
    "la evidencia no confirma",
    "no hay un incidente",
    "no existe un caso",
    "no está documentado",
    "no corresponde inventar",
)


def _contains(text: str, term: str) -> bool:
    return term.casefold() in text.casefold()


def _contains_any(text: str, terms: list[str]) -> bool:
    return not terms or any(_contains(text, term) for term in terms)


def _contains_private_ipv4(text: str) -> bool:
    return any(
        any(address in network for network in PRIVATE_IPV4_NETWORKS)
        for address in _valid_ipv4_addresses(text)
    )


def _valid_ipv4_addresses(text: str) -> list[ipaddress.IPv4Address]:
    addresses = []
    for candidate in IPV4_CANDIDATE.findall(text):
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if isinstance(address, ipaddress.IPv4Address):
            addresses.append(address)
    return addresses


def _known_evidence_ids(knowledge_path: Path) -> set[str]:
    identifiers = set()
    for document in knowledge_path.glob("*.md"):
        for line in document.read_text(encoding="utf-8").splitlines():
            if line.startswith("id:"):
                identifiers.add(line.partition(":")[2].strip())
                break
    return identifiers


def _load_cases(path: Path, knowledge_path: Path) -> list[dict]:
    cases = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not cases:
        raise ValueError("La matriz de contratos está vacía")
    identifiers = [case["id"] for case in cases]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("El conjunto contiene un ID duplicado")
    known_evidence = _known_evidence_ids(knowledge_path)
    if not known_evidence:
        raise ValueError("No se encontró el catálogo de procedencia autorizada")
    for case in cases:
        evidence = set(case.get("evidence_ids", []))
        allowed = set(case.get("allowed_evidence_ids", []))
        unknown = (evidence - allowed) | (allowed - known_evidence)
        if unknown:
            raise ValueError(
                f"El caso {case['id']} contiene procedencia no autorizada: "
                + ", ".join(sorted(unknown))
            )
    return cases


def _score_case(case: dict) -> dict[str, bool | None]:
    text = case["response"]
    first_sentence = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]
    evidence = set(case.get("evidence_ids", []))
    allowed = set(case.get("allowed_evidence_ids", []))
    required_labels = case.get("required_labels", [])
    story_terms = case.get("story_terms", {})
    forbidden_terms = case.get("forbidden_terms", [])
    text_without_ipv4 = text
    for address in _valid_ipv4_addresses(text):
        text_without_ipv4 = text_without_ipv4.replace(str(address), "")
    numeric_claims = set(re.findall(r"\b\d+\b", text_without_ipv4))
    allowed_numbers = {str(value) for value in case.get("allowed_numbers", [])}
    words = re.findall(r"\b[\wÁÉÍÓÚÜÑáéíóúüñ-]+\b", text)

    provenance_ok = evidence <= allowed and (
        bool(evidence) if case.get("requires_evidence", bool(allowed)) else not evidence
    )
    story_ok = all(
        _contains_any(text, alternatives)
        for alternatives in story_terms.values()
    )
    denial_ok = not case.get("no_denial_when_authorized", False) or not any(
        _contains(text, phrase) for phrase in NEGATIVE_DENIALS
    )
    junior_ok = not case.get("requires_junior", False) or _contains(text, "Junior")
    redirect_ok = not case.get("requires_redirect", False) or _contains_any(
        text, case.get("redirect_terms", [])
    )
    structure_ok = (
        case.get("min_words", 1) <= len(words) <= case.get("max_words", 160)
        and text.strip() == text
        and "\n\n\n" not in text
    )
    star_allowed = case.get("star_allowed")
    if star_allowed is True:
        behavioral_boundary_ok = all(label in text for label in STAR_LABELS)
    elif star_allowed is False:
        behavioral_boundary_ok = (
            not any(label in text for label in STAR_LABELS)
            and not any(_contains(text, term) for term in forbidden_terms)
            and not any(
                _contains(text, phrase)
                for phrase in BEHAVIORAL_NEGATIVE_PREAMBLES
            )
        )
    else:
        behavioral_boundary_ok = True

    direct_terms = case.get("direct_answer_terms", [])
    relevance_terms = case.get("relevance_terms", [])
    required_terms = case.get("required_terms", [])
    unsupported_claim_terms = case.get("unsupported_claim_terms", [])
    return {
        "directness": (
            _contains_any(first_sentence, direct_terms) if direct_terms else None
        ),
        "relevance": _contains_any(text, relevance_terms) if relevance_terms else None,
        "approved_evidence_references": provenance_ok,
        "evidence_labels": (
            all(_contains(text, label) for label in required_labels)
            if required_labels else None
        ),
        "project_problem_action_result": story_ok if story_terms else None,
        "behavioral_evidence_boundary": (
            behavioral_boundary_ok if star_allowed is not None else None
        ),
        "no_negative_denial": (
            denial_ok if case.get("no_denial_when_authorized", False) else None
        ),
        "junior_humility": (
            junior_ok and not any(_contains(text, claim) for claim in SENIOR_CLAIMS)
            if case.get("requires_junior", False)
            else None
        ),
        "no_senior_claim": not any(_contains(text, claim) for claim in SENIOR_CLAIMS),
        "forbidden_terms": not any(_contains(text, term) for term in forbidden_terms),
        "unapproved_numeric_claims": numeric_claims <= allowed_numbers,
        "reviewed_claim_sentinels": (
            not any(_contains(text, term) for term in unsupported_claim_terms)
            if unsupported_claim_terms else None
        ),
        "no_sensitive_disclosure": not any(
            pattern.search(text) for pattern in SENSITIVE_DISCLOSURE_PATTERNS
        ) and not _contains_private_ipv4(text),
        "concise_professional_structure": structure_ok,
        "required_content": (
            all(_contains(text, term) for term in required_terms)
            if required_terms else None
        ),
        "out_of_scope_redirect": (
            redirect_ok if case.get("requires_redirect", False) else None
        ),
    }


def run_response_contract_evaluation(
    cases_path: Path,
    output_path: Path,
    *,
    enforce_thresholds: bool = True,
    knowledge_path: Path = Path("knowledge"),
) -> dict:
    """Score reviewed offline response fixtures and write an auditable report."""

    cases = _load_cases(cases_path, knowledge_path)
    category_scores: dict[str, list[float]] = defaultdict(list)
    contract_scores: dict[str, list[float]] = defaultdict(list)
    failures: list[dict] = []
    core_failure_count = 0

    for case in cases:
        contracts = _score_case(case)
        failed = [name for name, passed in contracts.items() if passed is False]
        passed = not failed
        category_scores[case["category"]].append(1.0 if passed else 0.0)
        for name, result in contracts.items():
            if result is None:
                continue
            contract_scores[name].append(1.0 if result else 0.0)
        if failed:
            failures.append({"case_id": case["id"], "failed_contracts": failed})
            if case.get("core", True):
                core_failure_count += 1

    category_pass_rates = {
        category: round(mean(scores), 4)
        for category, scores in sorted(category_scores.items())
    }
    contract_pass_rates = {
        contract: round(mean(scores), 4)
        for contract, scores in sorted(contract_scores.items())
    }
    contract_counts = {
        contract: {"passed": int(sum(scores)), "applicable": len(scores)}
        for contract, scores in sorted(contract_scores.items())
    }
    category_counts = {
        category: {"passed": int(sum(scores)), "total": len(scores)}
        for category, scores in sorted(category_scores.items())
    }
    all_contract_results = [score for scores in contract_scores.values() for score in scores]
    report = {
        "mode": "offline_curated_response_contract_fixtures",
        "production_model_called": False,
        "case_count": len(cases),
        "metrics": {
            "overall_contract_pass_rate": round(mean(all_contract_results), 4),
            "overall_contract_passed": int(sum(all_contract_results)),
            "overall_contract_applicable": len(all_contract_results),
            "case_pass_rate": round(
                (len(cases) - len(failures)) / len(cases), 4
            ),
            "core_failure_count": core_failure_count,
        },
        "category_pass_floor": CATEGORY_PASS_FLOOR,
        "category_pass_rates": category_pass_rates,
        "category_counts": category_counts,
        "contract_pass_rates": contract_pass_rates,
        "contract_counts": contract_counts,
        "failures": failures,
        "limitation": (
            "Curated deterministic fixtures with reviewed term and numeric sentinels "
            "only; this is not general hallucination detection, and a one-shot "
            "production OpenAI response smoke is still required."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if enforce_thresholds:
        missed = [
            category
            for category, score in category_pass_rates.items()
            if score < CATEGORY_PASS_FLOOR
        ]
        reasons = []
        if core_failure_count:
            reasons.append("core_failure_count")
        if missed:
            reasons.append("Piso por categoría: " + ", ".join(missed))
        if reasons:
            raise SystemExit("Umbrales no alcanzados: " + "; ".join(reasons))
    return report


def main() -> None:
    report = run_response_contract_evaluation(
        Path("evals/response_contract_cases.jsonl"),
        Path("outputs/response_contract_evaluation.json"),
    )
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
