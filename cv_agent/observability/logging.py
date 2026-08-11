import json
import logging
from typing import Any


LOGGER = logging.getLogger("gael_cv_agent")


def log_event(event: str, **fields: Any) -> None:
    allowed = {
        "request_id",
        "route",
        "method",
        "status",
        "latency_ms",
        "model",
        "skill_name",
        "retrieval_hit_count",
    }
    payload = {"event": event}
    payload.update(
        {
            key: value
            for key, value in fields.items()
            if key in allowed
        }
    )
    LOGGER.info(json.dumps(payload, ensure_ascii=False))
