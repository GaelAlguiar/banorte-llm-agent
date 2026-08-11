from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_dockerfile_uses_python_312_and_non_root_user() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.12-slim" in dockerfile
    assert "USER appuser" in dockerfile
    assert "cv_agent ./cv_agent" in dockerfile
    assert "knowledge ./knowledge" in dockerfile
    assert "COPY . ." not in dockerfile


def test_sensitive_local_files_are_ignored() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")

    for marker in (
        ".env", "*.tfstate", "*.pem", "*.key", "*.db", "__pycache__/",
        "outputs/*.json", "*.pdf",
    ):
        assert marker in ignored


def test_example_environment_contains_names_without_secrets() -> None:
    example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "OPENAI_API_KEY=" in example
    assert "AGENT_API_KEY=" in example
    assert "sk-" not in example
    values = [
        line.split("=", 1)[1]
        for line in example.splitlines()
        if line.startswith(("OPENAI_API_KEY=", "AGENT_API_KEY="))
    ]
    assert values == ["", ""]
