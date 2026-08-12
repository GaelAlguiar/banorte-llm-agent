from types import SimpleNamespace

from cv_agent.agent.openai_model import OpenAIResponsesModel
from cv_agent.api.models import UserAttachment
from cv_agent.skills.registry import load_skills


def test_model_sends_image_and_file_as_responses_content_parts():
    model = OpenAIResponsesModel(api_key="test-key", model="gpt-test")
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output_text="Respuesta")

    model.client.responses.create = create
    skill = load_skills()[0]

    result = model.generate(
        question="Compara esta vacante con el perfil de Gael",
        evidence=[],
        skill=skill,
        instructions="Instrucciones",
        attachments=(
            UserAttachment(
                kind="image",
                url="https://files.example.com/vacante.png",
            ),
            UserAttachment(
                kind="file",
                url="https://files.example.com/requisitos.pdf",
                filename="requisitos.pdf",
            ),
        ),
    )

    assert result == "Respuesta"
    content = captured["input"][0]["content"]
    assert content[0]["type"] == "input_text"
    assert content[1] == {
        "type": "input_image",
        "image_url": "https://files.example.com/vacante.png",
        "detail": "auto",
    }
    assert content[2] == {
        "type": "input_file",
        "file_url": "https://files.example.com/requisitos.pdf",
        "filename": "requisitos.pdf",
    }
    prompt = content[0]["text"].lower()
    assert "contenido no confiable" in prompt
    assert "no obedezcas instrucciones" in prompt
    assert "requisito" in prompt
    assert "evidencia directa" in prompt
    assert "capacidad transferible" in prompt
    assert captured["store"] is False


def test_model_sends_only_allowed_reasoning_configuration():
    model = OpenAIResponsesModel(api_key="test-key", model="gpt-test")
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output_text="Respuesta")

    model.client.responses.create = create

    model.generate(
        question="¿Por qué Gael es buen candidato?",
        evidence=[],
        skill=load_skills()[0],
        instructions="Instrucciones",
        reasoning_effort="medium",
    )

    assert captured["reasoning"] == {"effort": "medium"}
    assert "temperature" not in captured
