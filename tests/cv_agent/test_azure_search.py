from cv_agent.retrieval.azure_search import AzureSearchRetrieval


class FakeEmbeddings:
    def embed(self, text):
        return [0.1, 0.2, 0.3]


class FakeSearchClient:
    def __init__(self, results=None):
        self.kwargs = None
        self.results = results or []

    def search(self, **kwargs):
        self.kwargs = kwargs
        return self.results


def result(score=0.91, *, section="Infraestructura", document_id="terraform-banregio"):
    return {
        "id": f"{document_id}--{section.lower()}",
        "document_id": document_id,
        "chunk_id": f"{document_id}--{section.lower()}",
        "section": section,
        "title": f"Terraform en Banregio — {section}",
        "category": "infraestructura",
        "evidence_level": "directa",
        "impact_type": "confirmado",
        "source_kind": "laboral",
        "source": "experiencia profesional",
        "content": "Infraestructura modular con Terraform.",
        "@search.score": score,
    }


def test_search_sends_text_vector_and_category_filter():
    client = FakeSearchClient([result()])
    retrieval = AzureSearchRetrieval(
        documents=[],
        client=client,
        embeddings=FakeEmbeddings(),
        min_score=0.03,
    )

    hits = retrieval.search(
        "experiencia con Terraform",
        top_k=3,
        categories={"infraestructura"},
    )

    assert hits[0].document_id == "terraform-banregio"
    assert hits[0].chunk_id == "terraform-banregio--infraestructura"
    assert hits[0].section == "Infraestructura"
    assert hits[0].score == 0.91
    assert client.kwargs["search_text"] == "experiencia con Terraform"
    assert client.kwargs["top"] == 9
    assert client.kwargs["filter"] == "category eq 'infraestructura'"
    vector_query = client.kwargs["vector_queries"][0]
    assert vector_query.fields == "content_vector"
    assert vector_query.k_nearest_neighbors == 9
    assert vector_query.vector == [0.1, 0.2, 0.3]


def test_search_escapes_filters_and_caps_top_k():
    client = FakeSearchClient([result()])
    retrieval = AzureSearchRetrieval(
        documents=[], client=client, embeddings=FakeEmbeddings()
    )

    hits = retrieval.search(
        "consulta",
        top_k=20,
        categories={"l'azure", "perfil"},
    )

    assert client.kwargs["top"] == 24
    assert len(hits) <= 8
    assert client.kwargs["filter"] == (
        "category eq 'l''azure' or category eq 'perfil'"
    )


def test_search_combines_categories_with_allowed_document_ids():
    client = FakeSearchClient([result()])
    retrieval = AzureSearchRetrieval(
        documents=[], client=client, embeddings=FakeEmbeddings()
    )

    retrieval.search(
        "consulta",
        categories={"proyecto", "habilidad"},
        allowed_document_ids={"terraform-banregio", "id'quoted"},
    )

    assert client.kwargs["filter"] == (
        "(category eq 'habilidad' or category eq 'proyecto') and "
        "(document_id eq 'id''quoted' or document_id eq 'terraform-banregio')"
    )


def test_search_defensively_discards_a_result_outside_the_allowlist():
    retrieval = AzureSearchRetrieval(
        documents=[],
        client=FakeSearchClient([result()]),
        embeddings=FakeEmbeddings(),
    )

    hits = retrieval.search(
        "consulta",
        allowed_document_ids={"different-authorized-document"},
    )

    assert hits == []


def test_search_discards_results_below_threshold():
    retrieval = AzureSearchRetrieval(
        documents=[],
        client=FakeSearchClient([result(score=0.02)]),
        embeddings=FakeEmbeddings(),
        min_score=0.03,
    )

    assert retrieval.search("consulta") == []


def test_ready_uses_a_minimal_search_request():
    client = FakeSearchClient([result()])
    retrieval = AzureSearchRetrieval(
        documents=[], client=client, embeddings=FakeEmbeddings()
    )

    assert retrieval.ready() is True
    assert client.kwargs == {
        "search_text": "*",
        "top": 1,
        "select": ["id"],
    }


def test_ready_returns_false_when_search_is_unavailable():
    class FailingClient:
        def search(self, **kwargs):
            raise RuntimeError("unavailable")

    retrieval = AzureSearchRetrieval(
        documents=[], client=FailingClient(), embeddings=FakeEmbeddings()
    )

    assert retrieval.ready() is False


def test_azure_search_limits_repeated_parent_but_keeps_distinct_sections():
    client = FakeSearchClient([
        result(0.95, section="Uno"),
        result(0.94, section="Dos"),
        result(0.93, section="Tres"),
        result(0.90, section="Otro", document_id="otro-proyecto"),
    ])
    retrieval = AzureSearchRetrieval(
        documents=[], client=client, embeddings=FakeEmbeddings()
    )

    hits = retrieval.search("consulta compuesta", top_k=4)

    assert [hit.section for hit in hits] == ["Uno", "Dos", "Otro"]
    assert client.kwargs["top"] == 12


def test_azure_diversity_fetches_candidates_beyond_first_eight_chunks():
    dominated = [
        result(0.99 - index / 100, section=f"Sección {index}")
        for index in range(8)
    ]
    later_sources = [
        result(
            0.80 - index / 100,
            section=f"Fuente {index}",
            document_id=f"proyecto-{index}",
        )
        for index in range(6)
    ]
    client = FakeSearchClient(dominated + later_sources)
    retrieval = AzureSearchRetrieval(
        documents=[], client=client, embeddings=FakeEmbeddings()
    )

    hits = retrieval.search("consulta compuesta", top_k=8)

    assert client.kwargs["top"] == 24
    assert len(hits) == 8
    assert len({hit.document_id for hit in hits}) == 7
