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
