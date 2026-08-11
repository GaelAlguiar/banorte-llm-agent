"""Compatibility entrypoint.

Run with:
    python -m uvicorn app:app --port 8000
"""

from cv_agent.main import create_app


app = create_app()


__all__ = ["app"]
