from types import SimpleNamespace

import pytest

from cv_agent.agent.professional_intent import (
    DeterministicProfessionalIntentClassifier,
    OpenAIProfessionalIntentClassifier,
)


def test_openai_professional_classifier_uses_question_only_strict_schema():
    classifier = OpenAIProfessionalIntentClassifier("test-key", "intent-model")
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output_text='{"classification":"capability"}')

    classifier.client.responses.create = create

    assert classifier.classify("¿Podría trabajar con Kafka?") == "capability"
    assert captured["model"] == "intent-model"
    assert captured["input"] == "¿Podría trabajar con Kafka?"
    assert captured["reasoning"] == {"effort": "none"}
    assert captured["store"] is False
    assert captured["max_output_tokens"] == 128
    schema = captured["text"]["format"]
    assert schema["strict"] is True
    assert schema["schema"]["properties"]["classification"]["enum"] == [
        "profile", "capability", "behavioral", "out_of_scope",
    ]


@pytest.mark.parametrize(
    "response_or_error",
    (
        SimpleNamespace(output_text="not-json"),
        SimpleNamespace(output_text='{"classification":"project"}'),
        RuntimeError("timeout"),
    ),
)
def test_openai_professional_classifier_fails_safe_out_of_scope(response_or_error):
    classifier = OpenAIProfessionalIntentClassifier("test-key", "intent-model")

    def create(**kwargs):
        if isinstance(response_or_error, Exception):
            raise response_or_error
        return response_or_error

    classifier.client.responses.create = create
    assert classifier.classify("consulta ambigua") == "out_of_scope"


@pytest.mark.parametrize(
    ("question", "expected"),
    (
        ("¿Cuál es el color favorito de Gael?", "out_of_scope"),
        ("¿Gael tiene mascotas?", "out_of_scope"),
        ("¿Qué libro prefiere Gael?", "out_of_scope"),
        ("¿Podría trabajar con Kafka?", "capability"),
        ("¿Qué conocimientos tiene de Pulumi?", "capability"),
        ("¿Ha usado Ray?", "capability"),
        ("¿Qué tan bueno sería en MLflow?", "capability"),
        ("Si le piden usar Argo CD, ¿cómo lo abordaría?", "capability"),
        ("¿Cómo sería trabajar con Gael?", "behavioral"),
        ("¿Cómo colabora con un equipo?", "behavioral"),
        ("Dame un resumen del perfil de Gael", "profile"),
    ),
)
def test_deterministic_professional_classifier_generalizes_by_intent(
    question, expected
):
    classifier = DeterministicProfessionalIntentClassifier()
    assert classifier.classify(question) == expected


def test_holdout_technologies_are_absent_from_implementation():
    from pathlib import Path
    import re

    implementation = "\n".join(
        path.read_text(encoding="utf-8").casefold()
        for path in Path("cv_agent").rglob("*.py")
    )
    for name in ("kafka", "pulumi", "ray", "mlflow", "argo cd"):
        assert re.search(rf"\b{re.escape(name)}\b", implementation) is None
