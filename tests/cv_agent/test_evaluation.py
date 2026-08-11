import json
from pathlib import Path

from cv_agent.evaluation.runner import run_evaluation


class Answer:
    def __init__(self) -> None:
        self.text = "Respuesta profesional con Azure, RAG y privacidad."
        self.skill_name = "role_fit"
        self.evidence_ids = ("ajuste-vacante-banorte",)


class DeterministicAgent:
    def answer(self, question: str) -> Answer:
        return Answer()


class StaticAgent:
    def __init__(self, answer) -> None:
        self._answer = answer

    def answer(self, question: str):
        return self._answer


def write_case(path: Path, **overrides) -> None:
    case = {
        "id": "case-01",
        "question": "pregunta",
        "expected_document_ids": [],
        "required_terms": [],
        "forbidden_terms": [],
        "expected_skill": "profile_summary",
        "category": "profile",
    }
    case.update(overrides)
    path.write_text(json.dumps(case, ensure_ascii=False) + "\n", encoding="utf-8")


def test_evaluation_reports_required_metrics(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    cases.write_text(
        json.dumps(
            {
                "id": "role-01",
                "question": "¿Por qué elegir a Gael para Banorte?",
                "expected_document_ids": ["ajuste-vacante-banorte"],
                "required_terms": ["Azure", "RAG"],
                "forbidden_terms": ["no sabe"],
                "expected_skill": "role_fit",
                "category": "role_fit",
                "requires_impact_story": True,
                "impact_terms": ["Azure"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    report = run_evaluation(
        cases,
        DeterministicAgent(),
        tmp_path / "report.json",
        enforce_thresholds=False,
    )

    assert set(report["metrics"]) >= {
        "retrieval_recall_at_k",
        "mrr",
        "groundedness",
        "privacy_pass_rate",
        "style_pass_rate",
        "tool_routing_accuracy",
        "impact_story_pass_rate",
        "latency_p95_ms",
    }
    assert report["metrics"]["retrieval_recall_at_k"] == 1.0
    assert report["metrics"]["impact_story_pass_rate"] == 1.0
    assert json.loads((tmp_path / "report.json").read_text())["case_count"] == 1


def test_empty_expected_evidence_rejects_unexpected_evidence(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    write_case(cases)

    report = run_evaluation(
        cases,
        DeterministicAgent(),
        tmp_path / "report.json",
        enforce_thresholds=False,
    )

    assert report["metrics"]["retrieval_recall_at_k"] == 0.0
    assert report["metrics"]["groundedness"] == 0.0
    assert report["failures"][0]["evidence_expectation_pass"] is False


def test_empty_expected_evidence_accepts_empty_answer_evidence(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    write_case(cases)
    answer = Answer()
    answer.evidence_ids = ()
    answer.skill_name = "profile_summary"

    report = run_evaluation(
        cases,
        StaticAgent(answer),
        tmp_path / "report.json",
        enforce_thresholds=False,
    )

    assert report["metrics"]["retrieval_recall_at_k"] == 1.0
    assert report["metrics"]["groundedness"] == 1.0
    assert report["failures"] == []


def test_impact_metric_uses_only_flagged_cases_and_requires_impact_content(
    tmp_path: Path,
) -> None:
    cases = tmp_path / "cases.jsonl"
    write_case(
        cases,
        expected_document_ids=["ajuste-vacante-banorte"],
        required_terms=["Azure"],
        requires_impact_story=True,
        impact_terms=["ahorro", "redujo"],
        expected_skill="role_fit",
    )
    unflagged = {
        "id": "case-02",
        "question": "otra pregunta",
        "expected_document_ids": ["ajuste-vacante-banorte"],
        "required_terms": ["Azure"],
        "forbidden_terms": [],
        "expected_skill": "role_fit",
        "category": "role_fit",
    }
    with cases.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(unflagged, ensure_ascii=False) + "\n")

    report = run_evaluation(
        cases,
        DeterministicAgent(),
        tmp_path / "report.json",
        enforce_thresholds=False,
    )

    assert report["metrics"]["impact_story_pass_rate"] == 0.0
    assert report["failures"][0]["impact_content_pass"] is False
    assert report["failures"][0]["impact_story_pass"] is False


def test_evaluation_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    row = {
        "id": "duplicado",
        "question": "pregunta",
        "expected_document_ids": [],
        "required_terms": [],
        "forbidden_terms": [],
        "expected_skill": "profile_summary",
        "category": "profile",
    }
    cases = tmp_path / "duplicates.jsonl"
    cases.write_text(
        "\n".join(json.dumps(row) for _ in range(2)) + "\n",
        encoding="utf-8",
    )

    try:
        run_evaluation(
            cases,
            DeterministicAgent(),
            tmp_path / "report.json",
            enforce_thresholds=False,
        )
    except ValueError as error:
        assert "duplicado" in str(error)
    else:
        raise AssertionError("Debió rechazar IDs duplicados")
