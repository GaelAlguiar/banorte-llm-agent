from dataclasses import asdict

from cv_agent.retrieval.service import HybridCvRetrieval


class ProfileTools:
    def __init__(self, retrieval: HybridCvRetrieval):
        self.retrieval = retrieval

    def search_profile(
        self,
        query: str,
        categories: list[str] | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        if not query.strip():
            raise ValueError("query es obligatorio")
        if not 1 <= top_k <= 8:
            raise ValueError("top_k debe estar entre 1 y 8")
        hits = self.retrieval.search(
            query,
            top_k=top_k,
            categories=set(categories) if categories else None,
        )
        return [asdict(hit) for hit in hits]

    def get_project(self, project_id: str) -> dict:
        allowed = {
            "proyectos-enerey",
            "proyectos-heytech",
            "genai-banorte-agent",
            "github-gael-alguiar",
        }
        if project_id not in allowed:
            raise ValueError("project_id no autorizado")
        document = next(
            item
            for item in self.retrieval.documents
            if item.id == project_id
        )
        return {
            "document_id": document.id,
            "title": document.title,
            "category": document.category,
            "evidence_level": document.evidence_level,
            "impact_type": document.impact_type,
            "source_kind": document.source_kind,
            "source": document.source,
            "excerpt": document.text,
        }
