import json

import numpy as np

from cv_agent.knowledge.models import KnowledgeDocument
from cv_agent.retrieval.ingest import (
    build_index,
    build_search_document,
    sync_documents,
)


class FakeEmbeddings:
    def embed(self, text):
        return [0.1, 0.2, 0.3]


def document(identifier="profile"):
    return KnowledgeDocument(
        id=identifier,
        title="Perfil",
        category="perfil",
        evidence_level="directa",
        impact_type="confirmado",
        source_kind="perfil",
        source="CV",
        text="Contenido",
        document_id=identifier,
        chunk_id=f"{identifier}--resumen",
        section="Resumen",
    )


def test_build_search_document_contains_metadata_hash_and_vector():
    result = build_search_document(document(), FakeEmbeddings())

    assert result["id"] == "profile--resumen"
    assert result["document_id"] == "profile"
    assert result["chunk_id"] == "profile--resumen"
    assert result["section"] == "Resumen"
    assert result["title"] == "Perfil"
    assert result["content"] == "Contenido"
    assert result["content_vector"] == [0.1, 0.2, 0.3]
    assert len(result["content_hash"]) == 64


def test_build_search_document_is_json_serializable_with_numpy_vector():
    class NumpyEmbeddings:
        def embed(self, text):
            return np.asarray([0.1, 0.2, 0.3], dtype=np.float32)

    result = build_search_document(document(), NumpyEmbeddings())

    encoded = json.dumps(result)
    assert "content_vector" in encoded
    assert all(type(value) is float for value in result["content_vector"])


class FakeSearchClient:
    def __init__(self):
        self.uploaded = []
        self.deleted = []

    def search(self, **kwargs):
        return [{"id": "old-id"}, {"id": "profile"}]

    def upload_documents(self, documents):
        self.uploaded.extend(documents)
        return [type("Result", (), {"succeeded": True})()]

    def delete_documents(self, documents):
        self.deleted.extend(documents)
        return [type("Result", (), {"succeeded": True})()]


def test_sync_uploads_current_documents_and_deletes_stale_ids():
    client = FakeSearchClient()

    summary = sync_documents(
        client=client,
        documents=[document()],
        embeddings=FakeEmbeddings(),
    )

    assert [item["id"] for item in client.uploaded] == ["profile--resumen"]
    assert client.deleted == [{"id": "old-id"}, {"id": "profile"}]
    assert summary == {"uploaded": 1, "deleted": 2}


def test_index_schema_adds_filterable_parent_and_section_fields():
    index = build_index("profile", 3)
    fields = {field.name: field for field in index.fields}

    assert fields["id"].key is True
    assert fields["document_id"].filterable is True
    assert fields["chunk_id"].filterable is True
    assert "section" in fields


def test_sync_fails_when_azure_rejects_an_upload():
    class RejectingClient(FakeSearchClient):
        def upload_documents(self, documents):
            return [type("Result", (), {"succeeded": False})()]

    try:
        sync_documents(
            client=RejectingClient(),
            documents=[document()],
            embeddings=FakeEmbeddings(),
        )
    except RuntimeError as error:
        assert "carga" in str(error).lower()
    else:
        raise AssertionError("La ingesta debió fallar")
