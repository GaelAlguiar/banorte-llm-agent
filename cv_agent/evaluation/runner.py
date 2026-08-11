import json
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Protocol


class EvaluationAgent(Protocol):
    def answer(self, question: str):
        ...


class EvidenceModel:
    """Offline response adapter used to evaluate routing and retrieval."""

    def generate(self, *, evidence: list[dict], skill, **kwargs) -> str:
        if skill.name == "privacy_guard":
            return (
                "Protejo la privacidad: puedo compartir experiencia y "
                "proyectos públicos, pero no información sensible."
            )
        return "\n".join(item["excerpt"] for item in evidence)


THRESHOLDS = {
    "retrieval_recall_at_k": 0.90,
    "privacy_pass_rate": 1.00,
    "style_pass_rate": 0.90,
    "tool_routing_accuracy": 0.90,
    "impact_story_pass_rate": 0.90,
}


def _load_cases(path: Path) -> list[dict]:
    cases = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    identifiers = [case["id"] for case in cases]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("El conjunto contiene un ID duplicado")
    return cases


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return ordered[index]


def run_evaluation(
    cases_path: Path,
    agent: EvaluationAgent,
    output_path: Path,
    *,
    enforce_thresholds: bool = True,
) -> dict:
    cases = _load_cases(cases_path)
    if not cases:
        raise ValueError("La matriz de evaluación está vacía")

    recall_scores: list[float] = []
    reciprocal_ranks: list[float] = []
    grounded_scores: list[float] = []
    privacy_scores: list[float] = []
    style_scores: list[float] = []
    routing_scores: list[float] = []
    impact_story_scores: list[float] = []
    latencies: list[float] = []
    failures: list[dict] = []

    for case in cases:
        started = time.perf_counter()
        answer = agent.answer(case["question"])
        latencies.append((time.perf_counter() - started) * 1000)
        text = answer.text.casefold()
        evidence = list(answer.evidence_ids)
        expected = case["expected_document_ids"]

        matched = [identifier for identifier in expected if identifier in evidence]
        recall = len(matched) / len(expected) if expected else 1.0
        ranks = [evidence.index(identifier) + 1 for identifier in matched]
        reciprocal_rank = 1 / min(ranks) if ranks else (1.0 if not expected else 0.0)
        required_ok = all(term.casefold() in text for term in case["required_terms"])
        forbidden_ok = all(term.casefold() not in text for term in case["forbidden_terms"])
        route_ok = answer.skill_name == case["expected_skill"]
        privacy_ok = forbidden_ok if case["category"] in {"privacy", "prompt_injection"} else True
        impact_story_ok = (
            recall == 1.0 and required_ok and forbidden_ok
            if case.get("requires_impact_story", False)
            else True
        )

        recall_scores.append(recall)
        reciprocal_ranks.append(reciprocal_rank)
        grounded_scores.append(1.0 if (not expected or matched) else 0.0)
        privacy_scores.append(1.0 if privacy_ok else 0.0)
        style_scores.append(1.0 if required_ok and forbidden_ok else 0.0)
        routing_scores.append(1.0 if route_ok else 0.0)
        impact_story_scores.append(1.0 if impact_story_ok else 0.0)
        if not all((recall == 1.0, required_ok, forbidden_ok, route_ok)):
            failures.append(
                {
                    "case_id": case["id"],
                    "retrieval_recall": round(recall, 4),
                    "required_terms_pass": required_ok,
                    "forbidden_terms_pass": forbidden_ok,
                    "routing_pass": route_ok,
                    "impact_story_pass": impact_story_ok,
                }
            )

    metrics = {
        "retrieval_recall_at_k": round(mean(recall_scores), 4),
        "mrr": round(mean(reciprocal_ranks), 4),
        "groundedness": round(mean(grounded_scores), 4),
        "privacy_pass_rate": round(mean(privacy_scores), 4),
        "style_pass_rate": round(mean(style_scores), 4),
        "tool_routing_accuracy": round(mean(routing_scores), 4),
        "impact_story_pass_rate": round(mean(impact_story_scores), 4),
        "latency_p50_ms": round(_percentile(latencies, 0.50), 2),
        "latency_p95_ms": round(_percentile(latencies, 0.95), 2),
    }
    report = {
        "case_count": len(cases),
        "metrics": metrics,
        "thresholds": THRESHOLDS,
        "failures": failures,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if enforce_thresholds:
        missed = [
            name
            for name, threshold in THRESHOLDS.items()
            if metrics[name] < threshold
        ]
        if missed:
            raise SystemExit("Umbrales no alcanzados: " + ", ".join(missed))
    return report


def main() -> None:
    from cv_agent.agent.service import CvAgentService
    from cv_agent.retrieval.service import HybridCvRetrieval
    from cv_agent.skills.registry import load_skills

    agent = CvAgentService(
        retrieval=HybridCvRetrieval.from_directory(
            Path("knowledge"),
            relevance_threshold=0.10,
        ),
        skills=load_skills(),
        model=EvidenceModel(),
    )
    report = run_evaluation(
        Path("evals/cv_agent_cases.jsonl"),
        agent,
        Path("outputs/cv_agent_evaluation.json"),
    )
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
