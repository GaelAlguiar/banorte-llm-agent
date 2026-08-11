import json

from openai import OpenAI

from cv_agent.api.models import UserAttachment
from cv_agent.skills.models import AgentSkill


class OpenAIResponsesModel:
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key, timeout=60.0)
        self.model = model

    def generate(
        self,
        *,
        question: str,
        evidence: list[dict],
        skill: AgentSkill,
        instructions: str,
        attachments: tuple[UserAttachment, ...] = (),
        reasoning_effort: str | None = None,
    ) -> str:
        evidence_payload = [
            {
                "title": item["title"],
                "category": item["category"],
                "evidence_level": item["evidence_level"],
                "impact_type": item["impact_type"],
                "source_kind": item["source_kind"],
                "excerpt": item["excerpt"],
            }
            for item in evidence
        ]
        text_part = (
            f"Skill seleccionada: {skill.name}\n"
            f"Reglas de salida: {'; '.join(skill.output_rules)}\n"
            "Evidencia autorizada:\n"
            f"{json.dumps(evidence_payload, ensure_ascii=False)}\n\n"
            f"Pregunta: {question}"
        )
        content: list[dict] = [{"type": "input_text", "text": text_part}]
        for attachment in attachments:
            if attachment.kind == "image":
                content.append({
                    "type": "input_image",
                    "image_url": attachment.url,
                    "detail": "auto",
                })
            else:
                file_part = {
                    "type": "input_file",
                    "file_url": attachment.url,
                }
                if attachment.filename:
                    file_part["filename"] = attachment.filename
                content.append(file_part)
        request_options = {
            "model": self.model,
            "instructions": instructions,
            "input": [{"role": "user", "content": content}],
            "store": False,
        }
        if reasoning_effort:
            request_options["reasoning"] = {"effort": reasoning_effort}
        response = self.client.responses.create(
            **request_options,
        )
        return response.output_text
