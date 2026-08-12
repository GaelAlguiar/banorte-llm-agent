import json
import time
import uuid
from collections.abc import Iterator
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from cv_agent.api.models import CreateResponseRequest, extract_user_input
from cv_agent.observability.logging import log_event
from cv_agent.security.auth import valid_bearer


router = APIRouter()


def _ident(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _message(message_id: str, text: str, status: str) -> dict[str, Any]:
    return {
        "id": message_id,
        "type": "message",
        "status": status,
        "role": "assistant",
        "content": [] if status != "completed" else [
            {
                "type": "output_text",
                "annotations": [],
                "text": text,
            }
        ],
    }


def _completed_response(
    response_id: str,
    message_id: str,
    text: str,
    created_at: int,
    evidence: tuple = (),
) -> dict[str, Any]:
    public_evidence = [asdict(item) for item in evidence]
    compact_ids = ",".join(
        item["chunk_id"] for item in public_evidence[:3]
    )[:512]
    return {
        "id": response_id,
        "object": "response",
        "model": "gael-cv-agent",
        "created_at": created_at,
        "status": "completed",
        "completed_at": int(time.time()),
        "output": [_message(message_id, text, "completed")],
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        },
        "error": None,
        # Open Responses metadata values are short strings. Detailed safe
        # evidence is an additive top-level extension for first-party clients.
        "metadata": ({"evidence_ids": compact_ids} if compact_ids else {}),
        "evidence": public_evidence,
    }


def _event(name: str, payload: dict[str, Any]) -> str:
    return (
        f"event: {name}\n"
        f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    )


def _stream_events(
    response_id: str,
    message_id: str,
    text: str,
    created_at: int,
    evidence: tuple = (),
) -> Iterator[str]:
    base = {
        "id": response_id,
        "object": "response",
        "model": "gael-cv-agent",
        "created_at": created_at,
    }
    empty_part = {"type": "output_text", "annotations": [], "text": ""}
    done_part = {"type": "output_text", "annotations": [], "text": text}
    completed = _completed_response(
        response_id,
        message_id,
        text,
        created_at,
        evidence,
    )
    events = [
        ("response.created", {"type": "response.created", "response": {**base, "status": "queued", "output": []}}),
        ("response.in_progress", {"type": "response.in_progress", "response": {**base, "status": "in_progress", "output": []}}),
        ("response.output_item.added", {"type": "response.output_item.added", "output_index": 0, "item": _message(message_id, "", "in_progress")}),
        ("response.content_part.added", {"type": "response.content_part.added", "item_id": message_id, "output_index": 0, "content_index": 0, "part": empty_part}),
        ("response.output_text.delta", {"type": "response.output_text.delta", "item_id": message_id, "output_index": 0, "content_index": 0, "delta": text}),
        ("response.output_text.done", {"type": "response.output_text.done", "item_id": message_id, "output_index": 0, "content_index": 0, "text": text}),
        ("response.content_part.done", {"type": "response.content_part.done", "item_id": message_id, "output_index": 0, "content_index": 0, "part": done_part}),
        ("response.output_item.done", {"type": "response.output_item.done", "output_index": 0, "item": _message(message_id, text, "completed")}),
        ("response.completed", {"type": "response.completed", "response": completed}),
    ]
    for sequence_number, (name, payload) in enumerate(events):
        payload["sequence_number"] = sequence_number
        yield _event(name, payload)
    yield "data: [DONE]\n\n"


@router.post("/v1/responses")
def create_response(body: CreateResponseRequest, request: Request):
    if not valid_bearer(
        request.headers.get("Authorization"),
        request.app.state.settings.agent_api_key,
    ):
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "message": "API key inválida o ausente.",
                    "type": "authentication_error",
                    "code": "invalid_api_key",
                    "param": None,
                }
            },
        )
    if body.previous_response_id is not None:
        return JSONResponse(
            status_code=400,
            content={"error": {
                "message": (
                    "previous_response_id no está soportado por este agente sin estado."
                ),
                "type": "invalid_request_error",
                "code": "unsupported_previous_response_id",
                "param": "previous_response_id",
            }},
        )
    try:
        user_input = extract_user_input(
            body.input,
            policy=request.app.state.attachment_policy,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    question = user_input.text
    if len(question) > 8_000:
        return JSONResponse(
            status_code=413,
            content={
                "error": {
                    "message": "El input excede 8000 caracteres.",
                    "type": "invalid_request_error",
                    "code": "input_too_large",
                    "param": "input",
                }
            },
        )
    agent = request.app.state.agent
    if agent is None:
        raise HTTPException(
            status_code=503,
            detail="El agente no está configurado.",
        )
    started = time.perf_counter()
    try:
        answer = agent.answer(
            question,
            attachments=user_input.attachments,
            reasoning_effort=(
                body.reasoning.effort if body.reasoning else None
            ),
            max_output_tokens=body.max_output_tokens,
        )
    except Exception:
        log_event(
            "agent_response",
            status="error",
            error_type="model_error",
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            attachment_count=min(len(user_input.attachments), 4),
            attachment_kinds=sorted({item.kind for item in user_input.attachments}),
        )
        raise
    log_event(
        "agent_response",
        status="success",
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
        skill_name=answer.skill_name,
        retrieval_hit_count=answer.retrieval_hit_count,
        source_kind_mix=list(answer.source_kind_mix),
        confidence_mix=list(answer.confidence_mix),
        attachment_count=answer.attachment_count,
        attachment_kinds=list(answer.attachment_kinds),
        safety_decision=answer.safety_decision,
    )
    answer_text = answer.text
    response_id = _ident("resp")
    message_id = _ident("msg")
    created_at = int(time.time())
    if body.stream:
        return StreamingResponse(
            _stream_events(
                response_id,
                message_id,
                answer_text,
                created_at,
                answer.evidence,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store"},
        )
    return _completed_response(
        response_id,
        message_id,
        answer_text,
        created_at,
        answer.evidence,
    )
