from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from flask import Flask, jsonify, render_template, request

from cv_agent.security.limits import SlidingWindowLimiter
from cv_agent.web.suggestions import SUGGESTED_QUESTIONS


def _error(status: int, message: str, code: str):
    return jsonify(
        {
            "error": {
                "message": message,
                "type": "invalid_request_error",
                "code": code,
                "param": "message",
            }
        }
    ), status


def create_flask_app(agent_provider: Callable[[], Any]) -> Flask:
    app = Flask(__name__)
    limiter = SlidingWindowLimiter()

    @app.after_request
    def security_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    @app.get("/")
    def chat_page():
        return render_template("chat.html", suggestions=SUGGESTED_QUESTIONS)

    @app.post("/api/messages")
    def create_message():
        if not request.is_json:
            return _error(415, "Se requiere JSON.", "unsupported_media_type")
        identity = request.remote_addr or "unknown"
        if not limiter.allow(identity):
            return _error(
                429,
                "Límite de 30 solicitudes por minuto excedido.",
                "rate_limit_exceeded",
            )
        payload = request.get_json(silent=True)
        message = payload.get("message") if isinstance(payload, dict) else None
        if not isinstance(message, str) or not message.strip():
            return _error(400, "El mensaje es obligatorio.", "invalid_message")
        message = message.strip()
        if len(message) > 8_000:
            return _error(413, "El mensaje excede 8000 caracteres.", "input_too_large")
        agent = agent_provider()
        if agent is None:
            return _error(503, "El agente no está disponible.", "agent_unavailable")
        try:
            answer = agent.answer(message)
        except Exception:
            app.logger.exception("agent_request_failed")
            return _error(502, "No fue posible generar la respuesta.", "agent_error")
        return jsonify({
            "response": answer.text,
            "evidence": [asdict(item) for item in answer.evidence],
        })

    return app
