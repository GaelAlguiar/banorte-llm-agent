import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.wsgi import WSGIMiddleware

from cv_agent.agent.openai_model import OpenAIResponsesModel
from cv_agent.agent.professional_intent import OpenAIProfessionalIntentClassifier
from cv_agent.agent.service import CvAgentService
from cv_agent.api.responses import router as responses_router
from cv_agent.api.models import AttachmentPolicy
from cv_agent.config import Settings
from cv_agent.observability.logging import log_event
from cv_agent.retrieval.factory import build_retrieval
from cv_agent.security.limits import SlidingWindowLimiter
from cv_agent.security.privacy_intent import OpenAIPrivacyIntentClassifier
from cv_agent.skills.registry import load_skills
from cv_agent.web.app import create_flask_app
from cv_agent.web.suggestions import SUGGESTED_QUESTIONS


def _build_agent(settings: Settings) -> CvAgentService | None:
    if not settings.openai_api_key:
        return None
    return CvAgentService(
        retrieval=build_retrieval(settings, Path("knowledge")),
        skills=load_skills(),
        model=OpenAIResponsesModel(
            api_key=settings.openai_api_key,
            model=settings.model,
        ),
        privacy_classifier=OpenAIPrivacyIntentClassifier(
            api_key=settings.openai_api_key,
            model=settings.privacy_classifier_model or settings.model,
        ),
        professional_classifier=OpenAIProfessionalIntentClassifier(
            api_key=settings.openai_api_key,
            model=settings.professional_classifier_model or settings.model,
        ),
        trusted_benign_questions=SUGGESTED_QUESTIONS,
    )


def create_app(
    settings: Settings | None = None,
    agent: Any | None = None,
) -> FastAPI:
    active_settings = settings or Settings.from_env()
    app = FastAPI(title="Gael CV Agent", version="1.0.0")
    app.state.settings = active_settings
    app.state.agent = agent if agent is not None else _build_agent(active_settings)
    app.state.rate_limiter = SlidingWindowLimiter()
    app.state.attachment_policy = AttachmentPolicy(
        max_attachments=active_settings.max_attachments,
        trusted_hosts=active_settings.trusted_attachment_hosts,
    )
    app.include_router(responses_router)

    @app.middleware("http")
    async def request_context(request, call_next):
        request_id = request.headers.get(
            "X-Request-ID",
            str(uuid.uuid4()),
        )
        started = time.perf_counter()
        response = await _apply_request_controls(request, call_next)
        latency_ms = round(
            (time.perf_counter() - started) * 1000,
            2,
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store"
        log_event(
            "http_request",
            request_id=request_id,
            route=request.url.path,
            method=request.method,
            status=response.status_code,
            latency_ms=latency_ms,
        )
        return response

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "gael-cv-agent",
        }

    @app.get("/health/ready")
    def readiness():
        active_agent = app.state.agent
        ready = bool(
            active_agent
            and active_agent.retrieval.ready()
        )
        content = {
            "status": "ready" if ready else "unavailable",
            "service": "gael-cv-agent",
        }
        if ready:
            return content
        return JSONResponse(status_code=503, content=content)

    flask_app = create_flask_app(lambda: app.state.agent)
    app.mount("/chat", WSGIMiddleware(flask_app))

    return app


def _error(status: int, message: str, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "message": message,
                "type": "invalid_request_error",
                "code": code,
                "param": None,
            }
        },
    )


async def _apply_request_controls(request: Request, call_next):
    if request.url.path != "/v1/responses" or request.method != "POST":
        return await call_next(request)
    content_type = request.headers.get("content-type", "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        return _error(415, "Se requiere Content-Type application/json.", "unsupported_media_type")
    try:
        content_length = int(request.headers.get("content-length", "0"))
    except ValueError:
        return _error(400, "Content-Length inválido.", "invalid_content_length")
    if content_length > 65_536:
        return _error(413, "El cuerpo excede 64 KiB.", "request_too_large")
    identity = request.client.host if request.client else "unknown"
    if not request.app.state.rate_limiter.allow(identity):
        return _error(429, "Límite de 30 solicitudes por minuto excedido.", "rate_limit_exceeded")
    return await call_next(request)
