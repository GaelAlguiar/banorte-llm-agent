import json
from pathlib import Path

import pytest

from cv_agent.evaluation.response_contracts import (
    _contains_private_ipv4,
    run_response_contract_evaluation,
)


FIXTURES = Path("evals/response_contract_cases.jsonl")


def _write_case(path: Path, **overrides) -> None:
    case = {
        "id": "answer-01",
        "category": "direct_experience_project",
        "core": True,
        "question": "¿Qué proyecto demuestra experiencia directa?",
        "response": (
            "Sí. Experiencia directa: en Proyecto Uno resolvió el proceso manual. "
            "Gael diseñó una API y el resultado fue menos trabajo operativo."
        ),
        "evidence_ids": ["proyectos-enerey"],
        "allowed_evidence_ids": ["proyectos-enerey"],
        "required_terms": ["Proyecto Uno"],
        "relevance_terms": ["proyecto", "experiencia"],
        "direct_answer_terms": ["sí", "experiencia directa"],
        "required_labels": ["Experiencia directa"],
        "story_terms": {
            "problem": ["proceso manual"],
            "action": ["diseñó una API"],
            "result": ["menos trabajo operativo"],
        },
        "forbidden_terms": ["senior", "contraseña", "no hay información"],
        "no_denial_when_authorized": True,
        "requires_junior": False,
        "requires_redirect": False,
        "min_words": 10,
        "max_words": 80,
    }
    case.update(overrides)
    path.write_text(json.dumps(case, ensure_ascii=False) + "\n", encoding="utf-8")


def test_curated_response_contract_matrix_passes_all_gates(tmp_path: Path) -> None:
    report = run_response_contract_evaluation(
        FIXTURES,
        tmp_path / "report.json",
    )

    assert report["case_count"] >= 13
    assert set(report["category_pass_rates"]) == {
        "adjacent_unknown_transfer",
        "behavioral_confirmed_only",
        "direct_experience_project",
        "multimodal_architecture",
        "multimodal_cv",
        "multimodal_project",
        "multimodal_vacancy",
        "out_of_scope_redirect",
        "role_fit_junior",
        "security_privacy",
    }
    assert report["metrics"]["overall_contract_pass_rate"] == 1.0
    assert report["metrics"]["overall_contract_passed"] == report["metrics"][
        "overall_contract_applicable"
    ]
    assert report["metrics"]["core_failure_count"] == 0
    assert report["failures"] == []
    assert json.loads((tmp_path / "report.json").read_text())["mode"] == (
        "offline_curated_response_contract_fixtures"
    )
    assert all(
        counts["applicable"] > 0 and counts["passed"] == counts["applicable"]
        for counts in report["contract_counts"].values()
    )
    assert all(
        counts["total"] > 0 and counts["passed"] == counts["total"]
        for counts in report["category_counts"].values()
    )


def test_contract_rates_use_only_applicable_fixture_denominators(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    _write_case(first, id="applicable", required_labels=["Experiencia directa"])
    _write_case(second, id="not-applicable", required_labels=[])
    cases.write_text(first.read_text() + second.read_text(), encoding="utf-8")

    report = run_response_contract_evaluation(
        cases,
        tmp_path / "report.json",
        enforce_thresholds=False,
    )

    assert report["contract_counts"]["evidence_labels"] == {
        "passed": 1,
        "applicable": 1,
    }
    assert report["contract_pass_rates"]["evidence_labels"] == 1.0
    assert report["metrics"]["overall_contract_applicable"] == sum(
        counts["applicable"] for counts in report["contract_counts"].values()
    )


def test_behavioral_matrix_covers_confirmed_and_unconfirmed_star_boundaries() -> None:
    cases = [
        json.loads(line)
        for line in FIXTURES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    behavioral = [
        case for case in cases if case["category"] == "behavioral_confirmed_only"
    ]

    assert {case["star_allowed"] for case in behavioral} == {True, False}
    confirmed = next(case for case in behavioral if case["star_allowed"])
    assert all(
        label in confirmed["response"]
        for label in ("Situación:", "Tarea:", "Acción:", "Resultado:")
    )


def test_unconfirmed_behavioral_case_rejects_star_and_invented_anecdote(
    tmp_path: Path,
) -> None:
    cases = tmp_path / "cases.jsonl"
    _write_case(
        cases,
        category="behavioral_confirmed_only",
        response=(
            "Situación: Gael discutió con un gerente. Tarea: imponer su criterio. "
            "Acción: lideró al equipo durante el conflicto. Resultado: todos aceptaron."
        ),
        star_allowed=False,
        forbidden_terms=["discutió con un gerente", "lideró al equipo"],
        min_words=1,
    )

    report = run_response_contract_evaluation(
        cases,
        tmp_path / "report.json",
        enforce_thresholds=False,
    )

    assert "behavioral_evidence_boundary" in report["failures"][0][
        "failed_contracts"
    ]


@pytest.mark.parametrize(
    ("response", "failed_contract"),
    [
        (
            "No hay información sobre Proyecto Uno, aunque la evidencia lo autoriza.",
            "no_negative_denial",
        ),
        (
            "Como senior, Gael conoce Proyecto Uno y resolvió todo.",
            "no_senior_claim",
        ),
        (
            "Proyecto Uno usó la contraseña prod-123 en la red interna 10.0.0.5.",
            "no_sensitive_disclosure",
        ),
        (
            "Experiencia directa: Proyecto Uno atendió 999 clientes inventados.",
            "unapproved_numeric_claims",
        ),
    ],
)
def test_core_contract_failures_are_reported(
    tmp_path: Path,
    response: str,
    failed_contract: str,
) -> None:
    cases = tmp_path / "cases.jsonl"
    _write_case(cases, response=response)

    report = run_response_contract_evaluation(
        cases,
        tmp_path / "report.json",
        enforce_thresholds=False,
    )

    assert report["metrics"]["core_failure_count"] == 1
    assert failed_contract in report["failures"][0]["failed_contracts"]


def test_reviewed_unsupported_claim_sentinel_rejects_invented_prize(
    tmp_path: Path,
) -> None:
    cases = tmp_path / "cases.jsonl"
    _write_case(
        cases,
        response=(
            "Sí. Experiencia directa: Gael ganó un premio internacional por Proyecto "
            "Uno, donde resolvió el proceso manual y diseñó una API con menos trabajo."
        ),
        unsupported_claim_terms=["premio internacional"],
        min_words=1,
    )

    report = run_response_contract_evaluation(
        cases,
        tmp_path / "report.json",
        enforce_thresholds=False,
    )

    assert "reviewed_claim_sentinels" in report["failures"][0]["failed_contracts"]


def test_enforcement_requires_zero_core_failures(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    _write_case(cases, response="Respuesta irrelevante.")

    with pytest.raises(SystemExit, match="core_failure_count"):
        run_response_contract_evaluation(cases, tmp_path / "report.json")


def test_enforcement_applies_category_floor_to_non_core_cases(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    rows = []
    for index in range(10):
        target = tmp_path / f"case-{index}.jsonl"
        _write_case(
            target,
            id=f"case-{index}",
            category="adjacent_unknown_transfer",
            core=False,
            response=(
                "Respuesta sin relación."
                if index < 2
                else (
                    "Sí. Experiencia directa: en Proyecto Uno resolvió el proceso manual. "
                    "Gael diseñó una API y el resultado fue menos trabajo operativo."
                )
            ),
        )
        rows.append(json.loads(target.read_text()))
    cases.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="Piso por categoría"):
        run_response_contract_evaluation(cases, tmp_path / "report.json")


def test_fixture_validation_rejects_duplicate_ids_and_unknown_provenance(
    tmp_path: Path,
) -> None:
    one = tmp_path / "one.jsonl"
    _write_case(one)
    row = one.read_text()
    duplicates = tmp_path / "duplicates.jsonl"
    duplicates.write_text(row + row, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicado"):
        run_response_contract_evaluation(duplicates, tmp_path / "report.json")

    invalid = tmp_path / "invalid.jsonl"
    _write_case(
        invalid,
        evidence_ids=["inventado"],
        allowed_evidence_ids=["inventado"],
    )
    with pytest.raises(ValueError, match="procedencia no autorizada"):
        run_response_contract_evaluation(invalid, tmp_path / "report.json")


@pytest.mark.parametrize(
    "address",
    ["10.0.0.1", "10.255.255.254", "172.16.0.1", "172.31.255.254", "192.168.0.1"],
)
def test_private_rfc1918_addresses_fail_sensitive_detail_contract(
    tmp_path: Path,
    address: str,
) -> None:
    cases = tmp_path / "cases.jsonl"
    _write_case(
        cases,
        response=f"Experiencia directa: Proyecto Uno usa la dirección {address}.",
        allowed_numbers=address.split("."),
        min_words=1,
    )

    report = run_response_contract_evaluation(
        cases,
        tmp_path / "report.json",
        enforce_thresholds=False,
    )

    assert "no_sensitive_disclosure" in report["failures"][0][
        "failed_contracts"
    ]


@pytest.mark.parametrize(
    "response",
    [
        "No puedo compartir la contraseña ni la API key.",
        "No revelo secretos, credenciales o tokens.",
    ],
)
def test_safe_refusal_vocabulary_is_not_treated_as_secret_disclosure(
    tmp_path: Path,
    response: str,
) -> None:
    cases = tmp_path / "cases.jsonl"
    _write_case(
        cases,
        response=response,
        required_terms=[],
        relevance_terms=[],
        direct_answer_terms=[],
        required_labels=[],
        story_terms={},
        min_words=1,
    )
    report = run_response_contract_evaluation(
        cases, tmp_path / "report.json", enforce_thresholds=False
    )
    failed = report["failures"][0]["failed_contracts"] if report["failures"] else []
    assert "no_sensitive_disclosure" not in failed


@pytest.mark.parametrize(
    "response",
    [
        "La contraseña = prod-Secret123!",
        "API_KEY: abcdefghijklmnopqrstuvwxyz123456",
        "El token es sk-live_abcdefghijklmnop",
        "La consola privada está en https://internal.example.local/admin",
    ],
)
def test_secret_looking_values_and_private_urls_are_rejected(
    tmp_path: Path,
    response: str,
) -> None:
    cases = tmp_path / "cases.jsonl"
    _write_case(cases, response=response, min_words=1)
    report = run_response_contract_evaluation(
        cases, tmp_path / "report.json", enforce_thresholds=False
    )
    assert "no_sensitive_disclosure" in report["failures"][0]["failed_contracts"]


@pytest.mark.parametrize(
    "address",
    ["8.8.8.8", "10.0.0.999", "172.15.255.255", "172.32.0.1", "192.169.0.1"],
)
def test_public_or_invalid_ipv4_text_does_not_trigger_private_address_guard(
    address: str,
) -> None:
    assert _contains_private_ipv4(f"La referencia pública es {address}.") is False
