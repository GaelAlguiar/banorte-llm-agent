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


def result(score=0.91):
    return {
        "id": "terraform-banregio",
        "title": "Terraform en Banregio",
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
    assert hits[0].score == 0.91
    assert client.kwargs["search_text"] == "experiencia con Terraform"
    assert client.kwargs["top"] == 3
    assert client.kwargs["filter"] == "category eq 'infraestructura'"
    vector_query = client.kwargs["vector_queries"][0]
    assert vector_query.fields == "content_vector"
    assert vector_query.k_nearest_neighbors == 5
    assert vector_query.vector == [0.1, 0.2, 0.3]


def test_search_escapes_filters_and_caps_top_k():
    client = FakeSearchClient([result()])
    retrieval = AzureSearchRetrieval(
        documents=[], client=client, embeddings=FakeEmbeddings()
    )

    retrieval.search(
        "consulta",
        top_k=20,
        categories={"l'azure", "perfil"},
    )

    assert client.kwargs["top"] == 8
    assert client.kwargs["filter"] == (
        "category eq 'l''azure' or category eq 'perfil'"
    )


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
