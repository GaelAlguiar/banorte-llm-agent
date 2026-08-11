from pathlib import Path


def test_cv_agent_does_not_import_legacy_demo() -> None:
    project_root = Path(__file__).parents[2]
    python_files = (project_root / "cv_agent").rglob("*.py")

    legacy_imports = [
        str(path.relative_to(project_root))
        for path in python_files
        if "rag_app" in path.read_text(encoding="utf-8")
    ]

    assert legacy_imports == []
