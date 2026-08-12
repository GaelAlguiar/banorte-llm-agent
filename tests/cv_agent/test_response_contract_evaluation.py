import json
from pathlib import Path

import pytest

from cv_agent.evaluation.response_contracts import run_response_contract_evaluation


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

    assert report["case_count"] >= 12
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
    assert report["metrics"]["core_failure_count"] == 0
    assert report["failures"] == []
    assert json.loads((tmp_path / "report.json").read_text())["mode"] == (
        "offline_curated_response_contract_fixtures"
    )


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
            "no_sensitive_or_invented_details",
        ),
        (
            "Experiencia directa: Proyecto Uno atendió 999 clientes inventados.",
            "no_sensitive_or_invented_details",
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
