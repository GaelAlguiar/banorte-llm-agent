import json
import logging
from numbers import Real
from typing import Any


LOGGER = logging.getLogger("gael_cv_agent")

_EVENTS = frozenset({"http_request", "agent_response"})
_SKILLS = frozenset({
    "architecture_explainer", "attachment_analysis", "behavioral_interview",
    "capability_advisor", "learning_evidence", "privacy_guard",
    "profile_summary", "project_story", "role_fit",
})
_ENUMS = {
    "method": frozenset({"GET", "POST"}),
    "status": frozenset({"success", "error"}),
    "skill_name": _SKILLS,
    "safety_decision": frozenset({"allowed", "blocked"}),
    "error_type": frozenset({"agent_error"}),
}
_LIST_ENUMS = {
    "source_kind_mix": frozenset({"perfil", "laboral", "demostrativo"}),
    "confidence_mix": frozenset({"alta", "media", "contextual"}),
    "attachment_kinds": frozenset({"image", "file"}),
}


def configure_logging(handler: logging.Handler | None = None) -> None:
    """Enable allowlisted operational events without changing global logging."""
    LOGGER.setLevel(logging.INFO)
    if handler is not None and handler not in LOGGER.handlers:
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(message)s"))
        LOGGER.addHandler(handler)
    elif handler is None and not LOGGER.handlers and not logging.getLogger().handlers:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(logging.Formatter("%(message)s"))
        LOGGER.addHandler(stream_handler)
    LOGGER.propagate = not bool(LOGGER.handlers)


def _safe_field(key: str, value: Any) -> Any | None:
    if key == "status" and isinstance(value, int) and 100 <= value <= 599:
        return value
    if key in _ENUMS:
        return value if value in _ENUMS[key] else None
    if key in _LIST_ENUMS and isinstance(value, (list, tuple)):
        return [item for item in value if item in _LIST_ENUMS[key]]
    if key == "latency_ms" and isinstance(value, Real) and not isinstance(value, bool):
        return round(min(max(float(value), 0.0), 120_000.0), 2)
    if key == "retrieval_hit_count" and isinstance(value, int) and not isinstance(value, bool):
        return min(max(value, 0), 8)
    if key == "attachment_count" and isinstance(value, int) and not isinstance(value, bool):
        return min(max(value, 0), 4)
    return None


def log_event(event: str, **fields: Any) -> None:
    if event not in _EVENTS:
        return
    payload = {"event": event}
    for key, value in fields.items():
        safe_value = _safe_field(key, value)
        if safe_value is not None:
            payload[key] = safe_value
    LOGGER.info(json.dumps(payload, ensure_ascii=False))
