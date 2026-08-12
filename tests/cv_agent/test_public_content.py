from pathlib import Path


def test_repository_has_no_irrelevant_dotnet_language_example():
    forbidden = "c" + "#"
    roots = (
        Path("cv_agent"),
        Path("evals"),
        Path("knowledge"),
        Path("tests"),
        Path("README.md"),
    )
    matches = []
    for root in roots:
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if path.is_file() and path.suffix in {".py", ".md", ".yaml", ".jsonl"}:
                if forbidden in path.read_text(encoding="utf-8").casefold():
                    matches.append(str(path))

    assert matches == []


def test_public_project_evidence_uses_reviewed_https_sources():
    enerey = Path("knowledge/03_proyectos_enerey.md").read_text(encoding="utf-8")
    freelance = Path("knowledge/17_freelance_global_lugra.md").read_text(
        encoding="utf-8"
    )
    readme = Path("README.md").read_text(encoding="utf-8")

    for url in (
        "https://enereylatam.com/",
        "https://apps.apple.com/mx/app/enerey/id6736633080",
    ):
        assert url in enerey
        assert url in readme
    for url in ("https://www.lugramx.com/", "https://globalfls.com/"):
        assert url in freelance
        assert url in readme
    assert "© Gael Alguiar" in enerey
    assert "no demuestra por sí sola cada componente" in " ".join(enerey.split())


def test_demo_documents_use_current_verified_counts():
    assert sum(1 for _ in Path("knowledge").glob("*.md")) == 17
    assert sum(1 for _ in Path("evals/cv_agent_cases.jsonl").open()) == 117
    video = Path("docs/VIDEO_DEMO_SCRIPT.md").read_text(encoding="utf-8")

    assert "diecisiete documentos" in video
    assert "noventa y siete casos" in video
    assert "doce documentos" not in video
    assert "ochenta pruebas" not in video
